import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { Shell } from "./components/Shell";
import { RunListPage } from "./pages/RunListPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { DiffPage } from "./pages/DiffPage";

const rootRoute = createRootRoute({
  component: () => (
    <Shell>
      <Outlet />
    </Shell>
  ),
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: RunListPage,
});

const runRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/run/$runId",
  component: RunDetailPage,
});

const diffRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/diff",
  validateSearch: (search: Record<string, unknown>) => ({
    a: String(search.a ?? ""),
    b: String(search.b ?? ""),
  }),
  component: DiffPage,
});

const routeTree = rootRoute.addChildren([indexRoute, runRoute, diffRoute]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
