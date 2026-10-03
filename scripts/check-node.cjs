"use strict";

var major = parseInt(String(process.versions.node).split(".")[0], 10);
if (major >= 22) {
  process.exit(0);
}

console.error("Range Bench needs Node.js 22. This machine is Node " + process.versions.node + ".");
console.error("From the repository root, run: sh scripts/install.sh");
console.error("That installs Node.js v22.23.3 into your home directory and then installs the page.");
process.exit(1);
