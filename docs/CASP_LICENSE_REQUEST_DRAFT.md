# Draft permission request for CASP-derived environment data

**To:** niclas.hertzberg@ai.se  
**Subject:** Redistribution and attribution guidance for a CASP-derived formal-verification RL environment

Hello Niclas,

I am preparing an open reinforcement-learning environment for fixed-contract C
completion, using Frama-C WP+RTE as the reward judge. The current research
corpus is a filtered and transformed subset of `nicher92/CASP_source_files`:
each admitted `file_content` record is re-verified, checked for vacuity, split
deterministically, and transformed into an ACSL contract plus a missing target
function body. The package would distribute the derived skeletons and reference
implementations so the environment can run reproducibly.

The CASP dataset card says the dataset is partly derived from The Stack 1 and 2
and advises users to check the underlying licenses. The `CASP_source_files`
records available to us contain `file_content` and `goals`, but not the original
repository URL, commit, path, copyright notice, or detected license. That means
we cannot currently produce correct per-record attribution or verify that
redistributing the transformed records is compatible with their source terms.

Could you please clarify one of the following?

1. Is there a license or written permission covering redistribution and
   modification of the CASP source-file records for an open research tool?
2. Is there a private or public mapping from each record to its original Stack
   repository/path/commit and detected license so we can preserve attribution
   and comply per record?
3. If redistribution is not intended, is linking to or downloading CASP at
   runtime the recommended use pattern?

We will cite the CASP paper and dataset prominently, retain the CASP record ID
where available, document our additional filtering, and avoid implying that
the original authors endorse the environment. I can share the exact derived
schema and proposed attribution file if that helps your review.

Thank you for the dataset and for any guidance you can provide.

Best,

[Name]  
[Project/repository URL]

## Internal note

Do not send this draft until the user adds their name and preferred project URL.
If permission is unavailable, the clean alternatives are: publish code only
with a user-supplied dataset path; reconstruct original Stack provenance and
licenses; or build a new corpus from repositories with explicit compatible
licenses and preserved attribution.
