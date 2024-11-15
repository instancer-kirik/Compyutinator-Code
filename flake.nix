{
  description = "My Project Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python312
            poetry
            qt6.full
            pkg-config
            git
            black
            pylint
            mypy
          ];

          shellHook = ''
            echo "Development environment loaded!"
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.qt6.qtbase}/lib/qt-${pkgs.qt6.qtbase.version}/plugins"
          '';
        };
      }
    );
}