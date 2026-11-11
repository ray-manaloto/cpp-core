# vcpkg overlay ports

Libraries vcpkg does not ship, or that need a patch, go here as overlay ports
(one directory per port: `vcpkg.json` + `portfile.cmake`). A port in `ports/`
always wins over a vcpkg port of the same name, so never shadow a vcpkg port by
accident: a shadowed library stops following the baseline pinned in `vcpkg.json`.

The directory is referenced by `vcpkg-configuration.json` (`overlay-ports`).
