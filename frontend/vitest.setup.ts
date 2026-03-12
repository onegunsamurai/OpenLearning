import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import React from "react";
import { afterEach, vi } from "vitest";

// Clean up after each test
afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

// Global mock for motion/react — renders plain HTML elements, strips animation props
vi.mock("motion/react", () => {
  const MOTION_PROPS = new Set([
    "initial",
    "animate",
    "exit",
    "transition",
    "variants",
    "whileHover",
    "whileTap",
    "whileFocus",
    "whileDrag",
    "whileInView",
    "layout",
    "layoutId",
    "onAnimationStart",
    "onAnimationComplete",
  ]);

  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (typeof prop === "symbol") return undefined;
      // Return a component that renders the HTML element, filtering motion props
      return ({
        children,
        ...props
      }: { children?: React.ReactNode } & Record<string, unknown>) => {
        const filtered: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(props)) {
          if (!MOTION_PROPS.has(key)) {
            filtered[key] = value;
          }
        }
        return React.createElement(prop, filtered, children);
      };
    },
  };

  return {
    motion: new Proxy({}, handler),
    AnimatePresence: ({
      children,
    }: {
      children?: React.ReactNode;
    }) => children,
  };
});
