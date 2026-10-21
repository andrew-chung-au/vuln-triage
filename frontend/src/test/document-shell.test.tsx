import { QueryClient } from "@tanstack/react-query";
import { RouterProvider, createMemoryHistory, createRouter } from "@tanstack/react-router";
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { routeTree } from "@/routeTree.gen";

// #34: index.html owns the document, so the root route must not render <html>
// inside #root. React reports that as "<html> cannot be a child of <div>".
describe("document shell", () => {
  it("renders the root route at / without an invalid DOM nesting warning", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = createRouter({
      routeTree,
      context: { queryClient },
      history: createMemoryHistory({ initialEntries: ["/"] }),
    });

    render(<RouterProvider router={router} />);
    await router.load();

    const messages = errorSpy.mock.calls.map((args) => args.map(String).join(" "));
    errorSpy.mockRestore();

    expect(messages.filter((m) => m.includes("cannot be a child of"))).toEqual([]);
  });
});
