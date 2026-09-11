import hashlib

from acsl_c.provenance import validate_record_provenance


def record(**updates):
    source = "/*@ ensures \\result == x; */\nint identity(int x) { return x; }\n"
    value = {
        "stable_id": "acslc:core-v1:identity",
        "dataset_id": "core-v1",
        "dataset_version": "0.1.0-draft",
        "source_kind": "project-authored",
        "source_repository_url": "pending-public-repository",
        "source_revision": "WORKTREE",
        "source_path": "core/identity.c",
        "source_content_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "license_spdx": "Apache-2.0",
        "copyright_notice": "Copyright 2026 project contributors",
        "transformation_description": "Target body replaced by TODO",
        "semantic_family": "scalar",
        "derivation_family": "identity",
        "review_status": "machine-verified-draft",
        "skeleton_c": source.replace("return x;", "// TODO: complete"),
        "reference_solution": source,
        "negative_cases": [
            {
                "name": "wrong",
                "candidate_source": source.replace("return x;", "return 0;"),
            }
        ],
    }
    value.update(updates)
    return value


def test_draft_provenance_accepts_complete_metadata():
    assert validate_record_provenance(record()) == []


def test_provenance_rejects_missing_license_and_wrong_hash():
    issues = validate_record_provenance(
        record(license_spdx="", source_content_sha256="0" * 64)
    )
    fields = {issue.field for issue in issues}
    assert {"license_spdx", "source_content_sha256"}.issubset(fields)


def test_final_release_rejects_draft_placeholders():
    issues = validate_record_provenance(record(), final_release=True)
    fields = {issue.field for issue in issues}
    assert {"source_repository_url", "source_revision", "review_status"}.issubset(
        fields
    )


def test_final_release_accepts_reviewed_pinned_source():
    value = record(
        dataset_version="1.0.0",
        source_repository_url="https://github.com/example/verified-rl-envs",
        source_revision="a" * 40,
        review_status="human-reviewed",
    )
    assert validate_record_provenance(value, final_release=True) == []
