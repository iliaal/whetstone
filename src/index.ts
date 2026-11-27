#!/usr/bin/env bun
import { defineCommand, runMain } from "citty"
import cleanup from "./commands/cleanup"
import convert from "./commands/convert"
import install from "./commands/install"
import listCommand from "./commands/list"
import sync from "./commands/sync"
import pkg from "../package.json"

const main = defineCommand({
  meta: {
    name: "whetstone",
    version: pkg.version,
    description: "Convert Claude Code plugins into other agent formats",
  },
  subCommands: {
    cleanup: () => cleanup,
    convert: () => convert,
    install: () => install,
    list: () => listCommand,
    sync: () => sync,
  },
})

runMain(main)
