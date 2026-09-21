import { validateProjectionEnvelope } from "./projection.mjs";

const entries = (value) => Object.entries(value);
const omit = (value, keys) =>
  Object.fromEntries(entries(value).filter(([key]) => !keys.includes(key)));

/** Loss-aware adaptation: preserve prose, extensions and opaque contracts verbatim. */
export function ethosClaimModel(input) {
  validateProjectionEnvelope(input, input?.digest);
  const sources = Object.fromEntries(
    input.source.bindings.map((row) => [
      row.id,
      {
        sha256: row.sha256,
        locator: row.path,
        authority: row.authority ?? input.authority.semantic_owner,
      },
    ]),
  );
  const copy = input.source.documents.find((row) => row.id === "copy");
  const copyId = "document:copy";
  if (Object.hasOwn(sources, copyId)) throw Error("Reserved semantic source identity: " + copyId);
  sources[copyId] = {
    sha256: copy.sha256,
    locator: copy.path,
    authority: input.authority.semantic_owner,
  };
  const claimSubject = "document:architecture-claims";
  const presentation = {
    title: input.title,
    authority: input.authority,
    quality: input.documents.quality_contract,
    view: input.view,
    viewProfile: input.documents.view_profile,
    copy: omit(input.documents.copy, ["assertions"]),
    extensions: {
      envelope: omit(input, [
        "schema",
        "digest",
        "title",
        "authority",
        "source",
        "documents",
        "semantics",
        "view",
      ]),
      semantics: omit(input.semantics, ["nodes", "relations", "contracts"]),
      documents: omit(input.documents, ["copy", "view_profile", "quality_contract"]),
    },
  };
  return {
    schema: "architecture.claim-model/v2",
    owner: input.source.id,
    vocabulary: {
      entities: [
        ...new Set(Object.values(input.semantics.nodes).map((v) => v.kind)),
        "semantic-subject",
      ].sort(),
      relations: [...new Set(input.semantics.relations.map((v) => v.kind))].sort(),
      maturities: ["declared"],
      predicates: {
        statement: {
          valueKind: "opaque",
          cardinality: "multiple",
          values: [],
          provenance: [copyId],
        },
      },
    },
    sources,
    entities: Object.fromEntries([
      ...entries(input.semantics.nodes).map(([id, value]) => [
        id,
        {
          type: value.kind,
          label: value.label,
          provenance: value.provenance,
          qualifiers: {
            attributes: value.attributes,
            extensions: omit(value, ["kind", "label", "attributes", "provenance"]),
          },
        },
      ]),
      [
        claimSubject,
        {
          type: "semantic-subject",
          label: "Published architecture claims",
          qualifiers: {},
          provenance: [copyId],
        },
      ],
    ]),
    relations: Object.fromEntries(
      input.semantics.relations.map((value) => [
        value.id,
        {
          type: value.kind,
          subject: value.from,
          object: value.to,
          provenance: value.provenance,
          qualifiers: {
            attributes: value.attributes,
            extensions: omit(value, ["id", "kind", "from", "to", "attributes", "provenance"]),
          },
        },
      ]),
    ),
    claims: Object.fromEntries(
      entries(input.documents.copy.assertions).map(([id, value]) => [
        id,
        {
          subject: claimSubject,
          predicate: "statement",
          object: null,
          value,
          plane: "published",
          condition: {},
          scope: {},
          maturity: "declared",
          validity: "affirmed",
          dependsOn: [],
          coverage: "unknown",
          provenance: [copyId],
        },
      ]),
    ),
    context: Object.fromEntries([
      ["documents:source-metadata", omit(input.source, ["id", "bindings"])],
      ...input.source.bindings.map((row) => [
        "documents:binding:" + row.id,
        omit(row, ["id", "sha256", "path", "authority"]),
      ]),
      ...entries(input.semantics.contracts).map(([key, value]) => ["contracts:" + key, value]),
      ...entries(presentation).map(([key, value]) => ["presentation:" + key, value]),
    ]),
  };
}
