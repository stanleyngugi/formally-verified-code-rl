from acsl_c.integrity import check_fixed_task_integrity

SKELETON = r"""
#include <limits.h>
/*@ requires 0 <= x <= 10;
    assigns \nothing;
    ensures \result == x + 1;
*/
int inc(int x) {
  // TODO: complete
}
"""

VALID = r"""
#include <limits.h>
/*@ requires 0 <= x <= 10;
    assigns \nothing;
    ensures \result == x + 1;
*/
int inc(int x) {
  /*@ assert x < INT_MAX; */
  return x + 1;
}
"""


def test_body_and_internal_annotations_may_change():
    result = check_fixed_task_integrity(VALID, SKELETON)
    assert result.ok


def test_contract_cannot_be_weakened():
    candidate = VALID.replace(r"ensures \result == x + 1;", r"ensures \true;")
    result = check_fixed_task_integrity(candidate, SKELETON)
    assert not result.ok
    assert not result.annotations_unchanged


def test_signature_and_surrounding_code_cannot_change():
    result = check_fixed_task_integrity(VALID.replace("int inc", "long inc"), SKELETON)
    assert not result.ok
    assert not result.context_unchanged


def test_braces_in_comments_and_literals_are_ignored():
    skeleton = "/* fake(int x) { } */\n/*@ ensures \\result == '{'; */\nchar f(void) { // TODO: complete\n}\n"
    candidate = "/* fake(int x) { } */\n/*@ ensures \\result == '{'; */\nchar f(void) { return '{';\n}\n"
    assert check_fixed_task_integrity(candidate, skeleton).ok
