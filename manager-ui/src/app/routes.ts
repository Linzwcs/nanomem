import { useEffect, useState } from "react";

export type Route =
  | { name: "overview" }
  | { name: "memory-units" }
  | { name: "memory-unit-detail"; unitId: string }
  | { name: "retrieval-preview" }
  | { name: "operations" }
  | { name: "index-health" };

export function useHashRoute(): Route {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const path = hash.replace(/^#\/?/, "");
  const routePath = path.split("?")[0];
  if (routePath.startsWith("memory-units/")) {
    return {
      name: "memory-unit-detail",
      unitId: decodeURIComponent(routePath.replace("memory-units/", "")),
    };
  }
  if (routePath === "memory-units") return { name: "memory-units" };
  if (routePath === "retrieval-preview") return { name: "retrieval-preview" };
  if (routePath === "operations") return { name: "operations" };
  if (routePath === "index-health") return { name: "index-health" };
  return { name: "overview" };
}
