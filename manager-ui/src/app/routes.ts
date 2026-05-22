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
  if (path.startsWith("memory-units/")) {
    return {
      name: "memory-unit-detail",
      unitId: decodeURIComponent(path.replace("memory-units/", "")),
    };
  }
  if (path === "memory-units") return { name: "memory-units" };
  if (path === "retrieval-preview") return { name: "retrieval-preview" };
  if (path === "operations") return { name: "operations" };
  if (path === "index-health") return { name: "index-health" };
  return { name: "overview" };
}
