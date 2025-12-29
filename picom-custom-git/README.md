# picom-custom-git

Custom picom build merging animations and features from multiple forks.

## Fork Sources

| Fork | Branch | Features | Status |
|------|--------|----------|--------|
| [yshui/picom](https://github.com/yshui/picom) | main | Base: dual_kawase blur, rounded corners, shadows | Active (v12.5) |
| [FT-Labs/picom](https://github.com/FT-Labs/picom) | next | 10+ animation types, desktop switching, inner border | Active |
| [pijulius/picom](https://github.com/pijulius/picom) | main | Workspace animations, animation-for-* options | Stale |
| [dccsillag/picom](https://github.com/dccsillag/picom) | implement-window-animations | Original animation implementation | Merged to pijulius |
| [jonaburg/picom](https://github.com/jonaburg/picom) | main | 40us time delta, spawn-center, size-transition | Stale |

## Merged Features

### From FT-Labs (primary animation source)
- 10+ animation types for window open/close
- Desktop/workspace switching animation
- Frame opacity for menubars/toolbars
- Inner border effect (edge pixel brightness)

### From pijulius
- animation-for-workspace-switch-in/out
- Extended animation type options

### From jonaburg
- transition-pow-x/y/w/h (easing parameters)
- spawn-center, spawn-center-screen
- no-scale-down option
- size-transition toggle

### Base (yshui/picom v12.5)
- dual_kawase blur (strength 0-20)
- Rounded corners
- GLX/EGL backends
- vsync control

## Build

```bash
makepkg -si
```

## Configuration

See picom.conf.example for all merged options.

Key animation settings:
```ini
animations = true;
animation-stiffness = 300;
animation-dampening = 20;
animation-window-mass = 1.0;
animation-clamping = false;

animation-for-open-window = "zoom";
animation-for-unmap-window = "squeeze";
animation-for-menu-window = "slide-down";
animation-for-transient-window = "slide-down";
animation-for-workspace-switch-in = "zoom";
animation-for-workspace-switch-out = "slide-down";
```

Available animation types:
- none, fade, zoom, slide-up, slide-down, slide-left, slide-right
- squeeze, squeeze-bottom, fly-in (FT-Labs)

## Merge Strategy

1. Clone yshui/picom as base
2. Add FT-Labs/picom as remote, fetch `next` branch
3. Cherry-pick animation commits from FT-Labs
4. Add pijulius/picom, cherry-pick workspace animation commits
5. Add jonaburg/picom, cherry-pick transition/spawn commits
6. Resolve conflicts manually
7. Test build

## References

- [Understanding picom forks](https://nuxsh.is-a.dev/blog/picom.html)
- [picom animations issue](https://github.com/yshui/picom/issues/1121)
- [FT-Labs animation PR](https://github.com/yshui/picom/pull/1109)
