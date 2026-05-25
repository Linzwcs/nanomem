import { describe, expect, it } from "vitest";

import { parseHashRoute } from "./routes";

describe("parseHashRoute", () => {
  it("parses session source dialogue deep links", () => {
    expect(parseHashRoute("#/sessions/demo?dialogue_id=dlg-1")).toEqual({
      name: "session-detail",
      sessionId: "demo",
      dialogueId: "dlg-1",
    });
  });

  it("parses plain session detail links without a highlighted dialogue", () => {
    expect(parseHashRoute("#/sessions/demo")).toEqual({
      name: "session-detail",
      sessionId: "demo",
      dialogueId: null,
    });
  });

  it("decodes route path ids", () => {
    expect(parseHashRoute("#/memory-units/unit%2F1")).toEqual({
      name: "memory-unit-detail",
      unitId: "unit/1",
    });
  });
});
