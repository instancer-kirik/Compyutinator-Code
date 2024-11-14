{
  description = "BigLinks Development Environment";

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
            # Python
            python312
            poetry
            
            # Qt dependencies
            qt6.full
            qt6.qtbase
            
            # System dependencies
            pkg-config
            
            # Development tools
            git
            
            # Optional but useful
            black
            pylint
            mypy
          ];

          shellHook = ''
            echo "BigLinks development environment loaded!"
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.qt6.qtbase.bin}/lib/qt-${pkgs.qt6.qtbase.version}/plugins"
          '';
        };
      }
    );
}