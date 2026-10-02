"use strict";

var major = parseInt(String(process.versions.node).split(".")[0], 10);
if (major >= 22) {
  process.exit(0);
}

console.error("Range Bench needs Node.js 22. This machine is Node " + process.versions.node + ".");
console.error("That is why with-app-env.mjs dies with Unexpected token {.");
console.error("Do not apt install nodejs. Put Node 22 in your home directory:");
console.error("  curl -fL -o /tmp/node22.tar.gz https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.gz");
console.error("  mkdir -p \"$HOME/.local/node22\"");
console.error("  tar -xzf /tmp/node22.tar.gz -C \"$HOME/.local/node22\" --strip-components=1");
console.error("  export PATH=\"$HOME/.local/node22/bin:$PATH\"");
console.error("Then run node -v, npm install, and npm run dev again from this folder.");
process.exit(1);
