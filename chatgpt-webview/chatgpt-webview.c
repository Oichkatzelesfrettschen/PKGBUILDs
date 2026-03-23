/*
 * chatgpt-webview -- minimal multi-tab WebKitGTK browser for ChatGPT
 *
 * Why:  Firefox leaks gigabytes of RAM on long ChatGPT sessions.  This
 *       wrapper runs ChatGPT in a dedicated WebKitGTK process with no
 *       extensions, no multi-process tab architecture, and a stripped
 *       feature set via webkit2gtk-4.1-hardened.
 *
 * What: GTK3 + WebKit2GTK-4.1 single-window app with a tab bar, cookie
 *       persistence, file upload/download, memory pressure management,
 *       and keyboard shortcuts. Tuned for low latency and low memory.
 *
 * Shortcuts: Ctrl+T new tab, Ctrl+W close tab, Ctrl+L reload,
 *            Ctrl+Tab / Ctrl+Shift+Tab cycle, Ctrl+Q quit.
 */

#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <string.h>

#define APP_NAME      "chatgpt-webview"
#define DEFAULT_URL   "https://chatgpt.com"
#define WINDOW_WIDTH  1200
#define WINDOW_HEIGHT 800

/* Memory pressure thresholds (MB). Aggressive to prevent the runaway
 * growth that makes ChatGPT tabs in Firefox consume 9+ GB. */
#define MEM_LIMIT_MB           512
#define MEM_CONSERVATIVE_PCT   0.50
#define MEM_STRICT_PCT         0.75
#define MEM_KILL_PCT           0.90
#define MEM_POLL_INTERVAL_SEC  5

/* -- state ---------------------------------------------------------------- */

static GtkNotebook *notebook;
static GtkWidget   *main_window;
static WebKitWebContext *web_context;

/* -- helpers -------------------------------------------------------------- */

static void
on_title_changed(WebKitWebView *wv, GParamSpec *ps, GtkLabel *label)
{
    (void)ps;
    const char *t = webkit_web_view_get_title(wv);
    if (!t || !*t) t = "New Tab";

    char buf[32];
    if (strlen(t) > 28) {
        memcpy(buf, t, 27);
        memcpy(buf + 27, "...", 4);
        gtk_label_set_text(label, buf);
    } else {
        gtk_label_set_text(label, t);
    }
}

static void
on_close_tab(GtkButton *btn, GtkWidget *page)
{
    (void)btn;
    int idx = gtk_notebook_page_num(notebook, page);
    if (idx >= 0)
        gtk_notebook_remove_page(notebook, idx);
    if (gtk_notebook_get_n_pages(notebook) == 0)
        gtk_main_quit();
}

/* -- file upload ---------------------------------------------------------- */

static gboolean
on_run_file_chooser(WebKitWebView *wv, WebKitFileChooserRequest *req,
                    gpointer data)
{
    (void)wv;
    (void)data;

    GtkWidget *dialog = gtk_file_chooser_dialog_new(
        "Upload File", GTK_WINDOW(main_window),
        GTK_FILE_CHOOSER_ACTION_OPEN,
        "_Cancel", GTK_RESPONSE_CANCEL,
        "_Open", GTK_RESPONSE_ACCEPT, NULL);

    gtk_file_chooser_set_select_multiple(GTK_FILE_CHOOSER(dialog),
        webkit_file_chooser_request_get_select_multiple(req));

    const char * const *mimes =
        webkit_file_chooser_request_get_mime_types(req);
    if (mimes && mimes[0]) {
        GtkFileFilter *filter = gtk_file_filter_new();
        gtk_file_filter_set_name(filter, "Allowed types");
        for (int i = 0; mimes[i]; i++)
            gtk_file_filter_add_mime_type(filter, mimes[i]);
        gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialog), filter);

        GtkFileFilter *all = gtk_file_filter_new();
        gtk_file_filter_set_name(all, "All files");
        gtk_file_filter_add_pattern(all, "*");
        gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialog), all);
    }

    if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT) {
        GSList *files = gtk_file_chooser_get_filenames(
            GTK_FILE_CHOOSER(dialog));
        guint n = g_slist_length(files);
        const char **paths = g_new0(const char *, n + 1);
        guint i = 0;
        for (GSList *l = files; l; l = l->next)
            paths[i++] = l->data;
        webkit_file_chooser_request_select_files(req, paths);
        g_free(paths);
        g_slist_free_full(files, g_free);
    } else {
        webkit_file_chooser_request_cancel(req);
    }

    gtk_widget_destroy(dialog);
    return TRUE;
}

/* -- file download -------------------------------------------------------- */

static gboolean
on_decide_destination(WebKitDownload *dl,
                      const char *suggested_filename,
                      gpointer data)
{
    (void)data;

    GtkWidget *dialog = gtk_file_chooser_dialog_new(
        "Save File", GTK_WINDOW(main_window),
        GTK_FILE_CHOOSER_ACTION_SAVE,
        "_Cancel", GTK_RESPONSE_CANCEL,
        "_Save", GTK_RESPONSE_ACCEPT, NULL);

    gtk_file_chooser_set_do_overwrite_confirmation(
        GTK_FILE_CHOOSER(dialog), TRUE);

    const char *dl_dir = g_get_user_special_dir(G_USER_DIRECTORY_DOWNLOAD);
    if (!dl_dir) dl_dir = g_get_home_dir();
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(dialog), dl_dir);

    if (suggested_filename && *suggested_filename)
        gtk_file_chooser_set_current_name(
            GTK_FILE_CHOOSER(dialog), suggested_filename);

    if (gtk_dialog_run(GTK_DIALOG(dialog)) == GTK_RESPONSE_ACCEPT) {
        char *path = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialog));
        char *uri = g_filename_to_uri(path, NULL, NULL);
        webkit_download_set_destination(dl, uri);
        g_free(uri);
        g_free(path);
        gtk_widget_destroy(dialog);
        return FALSE;
    }

    webkit_download_cancel(dl);
    gtk_widget_destroy(dialog);
    return FALSE;
}

static void
on_download_started(WebKitWebContext *ctx, WebKitDownload *dl, gpointer data)
{
    (void)ctx;
    (void)data;
    g_signal_connect(dl, "decide-destination",
                     G_CALLBACK(on_decide_destination), NULL);
}

/* -- webview creation ----------------------------------------------------- */

static WebKitWebView *
create_webview(void)
{
    WebKitSettings *settings = webkit_settings_new_with_settings(
        /* JS: required for ChatGPT */
        "enable-javascript", TRUE,
        "enable-javascript-markup", TRUE,
        "javascript-can-access-clipboard", TRUE,
        "javascript-can-open-windows-automatically", FALSE,

        /* Rendering: GPU-accelerated for smooth streaming responses */
        "hardware-acceleration-policy",
            WEBKIT_HARDWARE_ACCELERATION_POLICY_ON_DEMAND,
        "enable-webgl", TRUE,
        "enable-2d-canvas-acceleration", TRUE,
        "enable-smooth-scrolling", TRUE,

        /* Caching: page cache keeps back/forward pages in memory for
         * instant navigation. HTML5 local storage is needed for ChatGPT
         * settings and conversation state. DNS prefetching is on by
         * default in modern WebKit. */
        "enable-page-cache", TRUE,
        "enable-html5-local-storage", TRUE,
        "enable-html5-database", TRUE,

        /* Media: ChatGPT voice mode */
        "enable-media", TRUE,
        "enable-media-capabilities", TRUE,
        "enable-mediasource", TRUE,

        /* Disabled: features that waste memory or add latency */
        "enable-developer-extras", FALSE,
        "enable-back-forward-navigation-gestures", FALSE,
        "enable-java", FALSE,
        "enable-spatial-navigation", FALSE,
        "enable-frame-flattening", FALSE,
        "enable-site-specific-quirks", FALSE,
        "enable-write-console-messages-to-stdout", TRUE,

        NULL
    );

    WebKitWebView *wv = WEBKIT_WEB_VIEW(
        g_object_new(WEBKIT_TYPE_WEB_VIEW,
            "web-context", web_context,
            "settings", settings,
            NULL));

    g_signal_connect(wv, "run-file-chooser",
                     G_CALLBACK(on_run_file_chooser), NULL);

    g_object_unref(settings);
    return wv;
}

static void
add_tab(const char *url)
{
    WebKitWebView *wv = create_webview();
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_container_add(GTK_CONTAINER(scroll), GTK_WIDGET(wv));

    GtkWidget *hbox = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    GtkWidget *label = gtk_label_new("Loading...");
    gtk_label_set_max_width_chars(GTK_LABEL(label), 30);
    gtk_label_set_ellipsize(GTK_LABEL(label), PANGO_ELLIPSIZE_END);

    GtkWidget *close_btn = gtk_button_new_from_icon_name(
        "window-close-symbolic", GTK_ICON_SIZE_MENU);
    gtk_button_set_relief(GTK_BUTTON(close_btn), GTK_RELIEF_NONE);
    g_signal_connect(close_btn, "clicked", G_CALLBACK(on_close_tab), scroll);

    gtk_box_pack_start(GTK_BOX(hbox), label, TRUE, TRUE, 0);
    gtk_box_pack_end(GTK_BOX(hbox), close_btn, FALSE, FALSE, 0);
    gtk_widget_show_all(hbox);

    g_signal_connect(wv, "notify::title",
                     G_CALLBACK(on_title_changed), label);

    int idx = gtk_notebook_append_page(notebook, scroll, hbox);
    gtk_notebook_set_tab_reorderable(notebook, scroll, TRUE);
    gtk_widget_show_all(scroll);
    gtk_notebook_set_current_page(notebook, idx);

    webkit_web_view_load_uri(wv, url ? url : DEFAULT_URL);
}

/* -- keyboard shortcuts --------------------------------------------------- */

static gboolean
on_key_press(GtkWidget *w, GdkEventKey *ev, gpointer data)
{
    (void)w;
    (void)data;
    guint key = ev->keyval;
    guint mod = ev->state & gtk_accelerator_get_default_mod_mask();

    if (mod == GDK_CONTROL_MASK) {
        switch (key) {
        case GDK_KEY_t: add_tab(DEFAULT_URL); return TRUE;
        case GDK_KEY_w:
            on_close_tab(NULL,
                gtk_notebook_get_nth_page(notebook,
                    gtk_notebook_get_current_page(notebook)));
            return TRUE;
        case GDK_KEY_q: gtk_main_quit(); return TRUE;
        case GDK_KEY_l: {
            int cur = gtk_notebook_get_current_page(notebook);
            GtkWidget *page = gtk_notebook_get_nth_page(notebook, cur);
            GtkWidget *child = gtk_bin_get_child(GTK_BIN(page));
            if (WEBKIT_IS_WEB_VIEW(child))
                webkit_web_view_reload(WEBKIT_WEB_VIEW(child));
            return TRUE;
        }
        case GDK_KEY_Tab:
            gtk_notebook_next_page(notebook);
            return TRUE;
        default: break;
        }
    }
    if (mod == (GDK_CONTROL_MASK | GDK_SHIFT_MASK) &&
        key == GDK_KEY_ISO_Left_Tab) {
        gtk_notebook_prev_page(notebook);
        return TRUE;
    }

    return FALSE;
}

/* -- main ----------------------------------------------------------------- */

int
main(int argc, char *argv[])
{
    gtk_init(&argc, &argv);

    /* WebKit's GPU process needs EGL. On X11 with NVIDIA, the default EGL
     * platform detection can fail ("No provider of eglGetCurrentContext").
     * Force the X11 EGL platform explicitly. On Wayland this is a no-op
     * because WebKit detects it correctly. If compositing still fails,
     * the user can set WEBKIT_DISABLE_COMPOSITING_MODE=1 as a fallback,
     * but that breaks input event hit-testing. */
    if (!getenv("WEBKIT_DISABLE_DMABUF_RENDERER"))
        setenv("WEBKIT_DISABLE_DMABUF_RENDERER", "1", 0);

    /* Persistent data in XDG data dir */
    char *data_dir = g_build_filename(
        g_get_user_data_dir(), APP_NAME, NULL);
    g_mkdir_with_parents(data_dir, 0700);

    char *cache_dir = g_build_filename(
        g_get_user_cache_dir(), APP_NAME, NULL);
    g_mkdir_with_parents(cache_dir, 0700);

    char *cookie_path = g_build_filename(data_dir, "cookies.sqlite", NULL);

    /* Separate data and cache dirs: cache can be wiped without losing
     * session cookies or local storage. */
    WebKitWebsiteDataManager *data_mgr =
        webkit_website_data_manager_new(
            "base-data-directory", data_dir,
            "base-cache-directory", cache_dir,
            NULL);

    /* Memory pressure: aggressively reclaim memory to prevent the runaway
     * growth that plagues ChatGPT in Firefox. WebKit's memory pressure
     * handler runs in each web process and triggers GC, shrinks caches,
     * and releases decoded image data when thresholds are crossed. */
    WebKitMemoryPressureSettings *mem = webkit_memory_pressure_settings_new();
    webkit_memory_pressure_settings_set_memory_limit(mem, MEM_LIMIT_MB);
    /* Thresholds must be set in order: kill > strict > conservative */
    webkit_memory_pressure_settings_set_kill_threshold(
        mem, MEM_KILL_PCT);
    webkit_memory_pressure_settings_set_strict_threshold(
        mem, MEM_STRICT_PCT);
    webkit_memory_pressure_settings_set_conservative_threshold(
        mem, MEM_CONSERVATIVE_PCT);
    webkit_memory_pressure_settings_set_poll_interval(
        mem, MEM_POLL_INTERVAL_SEC);
    webkit_website_data_manager_set_memory_pressure_settings(mem);
    webkit_memory_pressure_settings_free(mem);

    web_context = webkit_web_context_new_with_website_data_manager(data_mgr);

    /* Cookies: persistent SQLite storage, block third-party trackers. */
    WebKitCookieManager *cookie_mgr =
        webkit_web_context_get_cookie_manager(web_context);
    webkit_cookie_manager_set_persistent_storage(
        cookie_mgr, cookie_path,
        WEBKIT_COOKIE_PERSISTENT_STORAGE_SQLITE);
    webkit_cookie_manager_set_accept_policy(
        cookie_mgr, WEBKIT_COOKIE_POLICY_ACCEPT_NO_THIRD_PARTY);

    g_signal_connect(web_context, "download-started",
                     G_CALLBACK(on_download_started), NULL);

    /* Cache model: WEB_BROWSER caches aggressively (disk + memory) for
     * lower latency on repeat visits and resource fetches. */
    webkit_web_context_set_cache_model(
        web_context, WEBKIT_CACHE_MODEL_WEB_BROWSER);

    g_free(cookie_path);
    g_free(cache_dir);
    g_free(data_dir);

    /* Window */
    main_window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(main_window), "ChatGPT");
    gtk_window_set_default_size(GTK_WINDOW(main_window),
                                WINDOW_WIDTH, WINDOW_HEIGHT);
    g_signal_connect(main_window, "destroy", G_CALLBACK(gtk_main_quit), NULL);
    g_signal_connect(main_window, "key-press-event",
                     G_CALLBACK(on_key_press), NULL);

    notebook = GTK_NOTEBOOK(gtk_notebook_new());
    gtk_notebook_set_scrollable(notebook, TRUE);
    gtk_container_add(GTK_CONTAINER(main_window), GTK_WIDGET(notebook));

    if (argc > 1) {
        for (int i = 1; i < argc; i++)
            add_tab(argv[i]);
    } else {
        add_tab(DEFAULT_URL);
    }

    gtk_widget_show_all(main_window);
    gtk_main();

    g_object_unref(web_context);
    g_object_unref(data_mgr);
    return 0;
}
