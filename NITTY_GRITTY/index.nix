{ pkgs ? import <nixpkgs> {} }:

let
  indexScript = pkgs.writeScriptBin "index-vault" ''
    #!${pkgs.stdenv.shell}
    set -euo pipefail

    VAULT_PATH="$1"
    
    ${pkgs.findutils}/bin/find "$VAULT_PATH" -type f \( \
      -name '*.md' -o \
      -name '*.txt' -o \
      -name '*.png' -o \
      -name '*.jpg' -o \
      -name '*.jpeg' -o \
      -name '*.gif' \
    \) -printf '%P\t%T@\t%s\t%y\n' | \
    ${pkgs.jq}/bin/jq -R -s 'split("\n") | map(select(length > 0)) | map(split("\t")) | map({
      path: .[0],
      mtime: .[1] | tonumber,
      size: .[2] | tonumber,
      type: if .[0] | test("\\.(png|jpg|jpeg|gif)$"; "i") then "image" else "document" end
    }) | {files: .}'
  '';
in
  pkgs.mkShell {
    buildInputs = [ indexScript ];
  }