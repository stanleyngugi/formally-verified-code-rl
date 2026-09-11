#!/usr/bin/env python3
"""Generate the project-authored Core-v1 task pack."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "packs" / "core-v1"
BODY_TOKEN = "/*__BODY__*/"


@dataclass(frozen=True)
class DraftTask:
    slug: str
    semantic_family: str
    derivation_family: str
    split: str
    template: str
    body: str
    wrong_body: str
    features: tuple[str, ...] = ()


BASE_TASKS = (
    DraftTask(
        "identity-int",
        "scalar-exact",
        "scalar-identity",
        "train",
        """/*@ assigns \\nothing;
    ensures \\result == x;
*/
int identity_int(int x) {
  /*__BODY__*/
}
""",
        "return x;",
        "return 0;",
    ),
    DraftTask(
        "increment-bounded",
        "bounded-arithmetic",
        "affine-plus-one",
        "train",
        """/*@ requires x <= 2147483646;
    assigns \\nothing;
    ensures \\result == x + 1;
*/
int increment_bounded(int x) {
  /*__BODY__*/
}
""",
        "return x + 1;",
        "return x;",
        ("overflow",),
    ),
    DraftTask(
        "decrement-bounded",
        "bounded-arithmetic",
        "affine-minus-one",
        "train",
        """/*@ requires x >= -2147483647;
    assigns \\nothing;
    ensures \\result == x - 1;
*/
int decrement_bounded(int x) {
  /*__BODY__*/
}
""",
        "return x - 1;",
        "return x;",
        ("overflow",),
    ),
    DraftTask(
        "negate-bounded",
        "bounded-arithmetic",
        "unary-negation",
        "train",
        """/*@ requires x >= -2147483647;
    assigns \\nothing;
    ensures \\result == -x;
*/
int negate_bounded(int x) {
  /*__BODY__*/
}
""",
        "return -x;",
        "return x;",
        ("overflow",),
    ),
    DraftTask(
        "add-bounded",
        "bounded-arithmetic",
        "binary-addition",
        "train",
        """/*@ requires -2147483648 <= a + b <= 2147483647;
    assigns \\nothing;
    ensures \\result == a + b;
*/
int add_bounded(int a, int b) {
  /*__BODY__*/
}
""",
        "return a + b;",
        "return a - b;",
        ("overflow",),
    ),
    DraftTask(
        "subtract-bounded",
        "bounded-arithmetic",
        "binary-subtraction",
        "train",
        """/*@ requires -2147483648 <= a - b <= 2147483647;
    assigns \\nothing;
    ensures \\result == a - b;
*/
int subtract_bounded(int a, int b) {
  /*__BODY__*/
}
""",
        "return a - b;",
        "return b - a;",
        ("overflow",),
    ),
    DraftTask(
        "square-bounded",
        "bounded-arithmetic",
        "bounded-square",
        "train",
        """/*@ requires -46340 <= x <= 46340;
    assigns \\nothing;
    ensures \\result == x * x;
*/
int square_bounded(int x) {
  /*__BODY__*/
}
""",
        "return x * x;",
        "return x + x;",
        ("overflow", "nonlinear"),
    ),
    DraftTask(
        "minimum-int",
        "branch-selection",
        "two-way-order",
        "train",
        """/*@ assigns \\nothing;
    ensures \\result <= a && \\result <= b;
    ensures \\result == a || \\result == b;
*/
int minimum_int(int a, int b) {
  /*__BODY__*/
}
""",
        "if (a < b) return a;\n  return b;",
        "if (a < b) return b;\n  return a;",
        ("branch",),
    ),
    DraftTask(
        "maximum-int",
        "branch-selection",
        "two-way-order",
        "train",
        """/*@ assigns \\nothing;
    ensures \\result >= a && \\result >= b;
    ensures \\result == a || \\result == b;
*/
int maximum_int(int a, int b) {
  /*__BODY__*/
}
""",
        "if (a > b) return a;\n  return b;",
        "if (a > b) return b;\n  return a;",
        ("branch",),
    ),
    DraftTask(
        "absolute-bounded",
        "piecewise-scalar",
        "absolute-value",
        "validation",
        """/*@ requires x >= -2147483647;
    assigns \\nothing;
    ensures \\result >= 0;
    ensures \\result == x || \\result == -x;
*/
int absolute_bounded(int x) {
  /*__BODY__*/
}
""",
        "if (x < 0) return -x;\n  return x;",
        "return x;",
        ("branch", "overflow"),
    ),
    DraftTask(
        "sign-int",
        "piecewise-scalar",
        "sign-classification",
        "validation",
        """/*@ assigns \\nothing;
    ensures x < 0 ==> \\result == -1;
    ensures x == 0 ==> \\result == 0;
    ensures x > 0 ==> \\result == 1;
*/
int sign_int(int x) {
  /*__BODY__*/
}
""",
        "if (x < 0) return -1;\n  if (x > 0) return 1;\n  return 0;",
        "if (x < 0) return 1;\n  return 0;",
        ("branch",),
    ),
    DraftTask(
        "clamp-int",
        "piecewise-scalar",
        "three-way-clamp",
        "validation",
        """/*@ requires lo <= hi;
    assigns \\nothing;
    ensures lo <= \\result <= hi;
    ensures x < lo ==> \\result == lo;
    ensures x > hi ==> \\result == hi;
    ensures lo <= x <= hi ==> \\result == x;
*/
int clamp_int(int x, int lo, int hi) {
  /*__BODY__*/
}
""",
        "if (x < lo) return lo;\n  if (x > hi) return hi;\n  return x;",
        "return x;",
        ("branch",),
    ),
    DraftTask(
        "swap-separated",
        "pointer-update",
        "two-cell-swap",
        "test",
        """/*@ requires \\valid(a) && \\valid(b);
    requires \\separated(a, b);
    assigns *a, *b;
    ensures *a == \\old(*b);
    ensures *b == \\old(*a);
*/
void swap_separated(int *a, int *b) {
  /*__BODY__*/
}
""",
        "int temporary = *a;\n  *a = *b;\n  *b = temporary;",
        "*a = *b;",
        ("pointer", "assigns", "separation"),
    ),
    DraftTask(
        "set-pair",
        "pointer-update",
        "two-cell-write",
        "test",
        """/*@ requires \\valid(first) && \\valid(second);
    requires \\separated(first, second);
    assigns *first, *second;
    ensures *first == x;
    ensures *second == y;
*/
void set_pair(int *first, int *second, int x, int y) {
  /*__BODY__*/
}
""",
        "*first = x;\n  *second = y;",
        "*first = y;\n  *second = x;",
        ("pointer", "assigns", "separation"),
    ),
    DraftTask(
        "conditional-store",
        "pointer-update",
        "conditional-cell-write",
        "test",
        """/*@ requires \\valid(out);
    assigns *out;
    ensures condition != 0 ==> *out == when_true;
    ensures condition == 0 ==> *out == when_false;
*/
void conditional_store(int *out, int condition, int when_true, int when_false) {
  /*__BODY__*/
}
""",
        "if (condition != 0) *out = when_true;\n  else *out = when_false;",
        "*out = when_true;",
        ("pointer", "assigns", "branch"),
    ),
    DraftTask(
        "swap-array-ends",
        "array-update",
        "bounded-two-cell-swap",
        "test",
        """/*@ requires n > 0;
    requires \\valid(a + (0 .. n - 1));
    assigns a[0], a[n - 1];
    ensures a[0] == \\old(a[n - 1]);
    ensures a[n - 1] == \\old(a[0]);
*/
void swap_array_ends(int *a, int n) {
  /*__BODY__*/
}
""",
        "int temporary = a[0];\n  a[0] = a[n - 1];\n  a[n - 1] = temporary;",
        "a[0] = a[n - 1];",
        ("pointer", "array", "assigns"),
    ),
)


def scalar_task(
    slug: str,
    semantic_family: str,
    derivation_family: str,
    split: str,
    contract: str,
    signature: str,
    body: str,
    wrong_body: str,
    features: tuple[str, ...] = (),
) -> DraftTask:
    template = f"/*@ {contract}\n*/\n{signature} {{\n  {BODY_TOKEN}\n}}\n"
    return DraftTask(
        slug,
        semantic_family,
        derivation_family,
        split,
        template,
        body,
        wrong_body,
        features,
    )


EXTRA_TASKS = (
    # Exact constants and bounded scalar arithmetic (training split).
    scalar_task(
        "constant-zero",
        "scalar-constant",
        "constant-zero",
        "train",
        "assigns \\nothing;\n    ensures \\result == 0;",
        "int constant_zero(void)",
        "return 0;",
        "return 1;",
    ),
    scalar_task(
        "constant-one",
        "scalar-constant",
        "constant-one",
        "train",
        "assigns \\nothing;\n    ensures \\result == 1;",
        "int constant_one(void)",
        "return 1;",
        "return 0;",
    ),
    scalar_task(
        "constant-minus-one",
        "scalar-constant",
        "constant-minus-one",
        "train",
        "assigns \\nothing;\n    ensures \\result == -1;",
        "int constant_minus_one(void)",
        "return -1;",
        "return 1;",
    ),
    scalar_task(
        "constant-forty-two",
        "scalar-constant",
        "constant-forty-two",
        "train",
        "assigns \\nothing;\n    ensures \\result == 42;",
        "int constant_forty_two(void)",
        "return 42;",
        "return 24;",
    ),
    scalar_task(
        "add-two-bounded",
        "bounded-offset",
        "offset-plus-two",
        "train",
        "requires x <= 2147483645;\n    assigns \\nothing;\n    ensures \\result == x + 2;",
        "int add_two_bounded(int x)",
        "return x + 2;",
        "return x + 1;",
        ("overflow",),
    ),
    scalar_task(
        "add-five-bounded",
        "bounded-offset",
        "offset-plus-five",
        "train",
        "requires x <= 2147483642;\n    assigns \\nothing;\n    ensures \\result == x + 5;",
        "int add_five_bounded(int x)",
        "return x + 5;",
        "return x + 4;",
        ("overflow",),
    ),
    scalar_task(
        "subtract-two-bounded",
        "bounded-offset",
        "offset-minus-two",
        "train",
        "requires x >= -2147483646;\n    assigns \\nothing;\n    ensures \\result == x - 2;",
        "int subtract_two_bounded(int x)",
        "return x - 2;",
        "return x - 1;",
        ("overflow",),
    ),
    scalar_task(
        "subtract-five-bounded",
        "bounded-offset",
        "offset-minus-five",
        "train",
        "requires x >= -2147483643;\n    assigns \\nothing;\n    ensures \\result == x - 5;",
        "int subtract_five_bounded(int x)",
        "return x - 5;",
        "return x - 4;",
        ("overflow",),
    ),
    scalar_task(
        "double-bounded",
        "bounded-scale",
        "scale-two",
        "train",
        "requires -1073741824 <= x <= 1073741823;\n    assigns \\nothing;\n    ensures \\result == 2 * x;",
        "int double_bounded(int x)",
        "return 2 * x;",
        "return x;",
        ("overflow",),
    ),
    scalar_task(
        "triple-bounded",
        "bounded-scale",
        "scale-three",
        "train",
        "requires -715827882 <= x <= 715827882;\n    assigns \\nothing;\n    ensures \\result == 3 * x;",
        "int triple_bounded(int x)",
        "return 3 * x;",
        "return 2 * x;",
        ("overflow",),
    ),
    scalar_task(
        "quadruple-bounded",
        "bounded-scale",
        "scale-four",
        "train",
        "requires -536870912 <= x <= 536870911;\n    assigns \\nothing;\n    ensures \\result == 4 * x;",
        "int quadruple_bounded(int x)",
        "return 4 * x;",
        "return 3 * x;",
        ("overflow",),
    ),
    scalar_task(
        "negative-double-bounded",
        "bounded-scale",
        "scale-negative-two",
        "train",
        "requires -1073741823 <= x <= 1073741824;\n    assigns \\nothing;\n    ensures \\result == -2 * x;",
        "int negative_double_bounded(int x)",
        "return -2 * x;",
        "return 2 * x;",
        ("overflow",),
    ),
    scalar_task(
        "is-zero",
        "integer-predicate",
        "predicate-zero",
        "train",
        "assigns \\nothing;\n    ensures 0 <= \\result <= 1;\n    ensures x == 0 ==> \\result == 1;\n    ensures x != 0 ==> \\result == 0;",
        "int is_zero(int x)",
        "if (x == 0) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "is-positive",
        "integer-predicate",
        "predicate-positive",
        "train",
        "assigns \\nothing;\n    ensures 0 <= \\result <= 1;\n    ensures x > 0 ==> \\result == 1;\n    ensures x <= 0 ==> \\result == 0;",
        "int is_positive(int x)",
        "if (x > 0) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "is-negative",
        "integer-predicate",
        "predicate-negative",
        "train",
        "assigns \\nothing;\n    ensures 0 <= \\result <= 1;\n    ensures x < 0 ==> \\result == 1;\n    ensures x >= 0 ==> \\result == 0;",
        "int is_negative(int x)",
        "if (x < 0) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "integers-equal",
        "integer-predicate",
        "predicate-equality",
        "train",
        "assigns \\nothing;\n    ensures 0 <= \\result <= 1;\n    ensures a == b ==> \\result == 1;\n    ensures a != b ==> \\result == 0;",
        "int integers_equal(int a, int b)",
        "if (a == b) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "integer-less-than",
        "integer-predicate",
        "predicate-less-than",
        "train",
        "assigns \\nothing;\n    ensures 0 <= \\result <= 1;\n    ensures a < b ==> \\result == 1;\n    ensures a >= b ==> \\result == 0;",
        "int integer_less_than(int a, int b)",
        "if (a < b) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "integer-in-range",
        "integer-predicate",
        "predicate-range",
        "train",
        "requires lo <= hi;\n    assigns \\nothing;\n    ensures 0 <= \\result <= 1;\n    ensures lo <= x <= hi ==> \\result == 1;\n    ensures x < lo || x > hi ==> \\result == 0;",
        "int integer_in_range(int x, int lo, int hi)",
        "if (x >= lo && x <= hi) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "select-nonzero",
        "scalar-selection",
        "select-on-nonzero",
        "train",
        "assigns \\nothing;\n    ensures condition != 0 ==> \\result == when_true;\n    ensures condition == 0 ==> \\result == when_false;",
        "int select_nonzero(int condition, int when_true, int when_false)",
        "if (condition != 0) return when_true;\n  return when_false;",
        "return when_true;",
        ("branch",),
    ),
    scalar_task(
        "select-zero",
        "scalar-selection",
        "select-on-zero",
        "train",
        "assigns \\nothing;\n    ensures condition == 0 ==> \\result == when_zero;\n    ensures condition != 0 ==> \\result == otherwise;",
        "int select_zero(int condition, int when_zero, int otherwise)",
        "if (condition == 0) return when_zero;\n  return otherwise;",
        "return otherwise;",
        ("branch",),
    ),
    scalar_task(
        "positive-part",
        "scalar-selection",
        "positive-part",
        "train",
        "assigns \\nothing;\n    ensures x > 0 ==> \\result == x;\n    ensures x <= 0 ==> \\result == 0;",
        "int positive_part(int x)",
        "if (x > 0) return x;\n  return 0;",
        "return x;",
        ("branch",),
    ),
    scalar_task(
        "negative-part",
        "scalar-selection",
        "negative-part",
        "train",
        "assigns \\nothing;\n    ensures x < 0 ==> \\result == x;\n    ensures x >= 0 ==> \\result == 0;",
        "int negative_part(int x)",
        "if (x < 0) return x;\n  return 0;",
        "return x;",
        ("branch",),
    ),
    scalar_task(
        "lower-bound",
        "scalar-selection",
        "lower-bound",
        "train",
        "assigns \\nothing;\n    ensures \\result >= lower;\n    ensures x < lower ==> \\result == lower;\n    ensures x >= lower ==> \\result == x;",
        "int lower_bound(int x, int lower)",
        "if (x < lower) return lower;\n  return x;",
        "return x;",
        ("branch",),
    ),
    scalar_task(
        "upper-bound",
        "scalar-selection",
        "upper-bound",
        "train",
        "assigns \\nothing;\n    ensures \\result <= upper;\n    ensures x > upper ==> \\result == upper;\n    ensures x <= upper ==> \\result == x;",
        "int upper_bound(int x, int upper)",
        "if (x > upper) return upper;\n  return x;",
        "return x;",
        ("branch",),
    ),
    # Held-out scalar composition families (validation split).
    scalar_task(
        "compare-to-pivot",
        "three-way-order",
        "pivot-comparison",
        "validation",
        "assigns \\nothing;\n    ensures x < pivot ==> \\result == -1;\n    ensures x == pivot ==> \\result == 0;\n    ensures x > pivot ==> \\result == 1;",
        "int compare_to_pivot(int x, int pivot)",
        "if (x < pivot) return -1;\n  if (x > pivot) return 1;\n  return 0;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "maximum-three",
        "three-way-order",
        "maximum-three",
        "validation",
        "assigns \\nothing;\n    ensures \\result >= a && \\result >= b && \\result >= c;\n    ensures \\result == a || \\result == b || \\result == c;",
        "int maximum_three(int a, int b, int c)",
        "int result = a;\n  if (b > result) result = b;\n  if (c > result) result = c;\n  return result;",
        "return a;",
        ("branch",),
    ),
    scalar_task(
        "minimum-three",
        "three-way-order",
        "minimum-three",
        "validation",
        "assigns \\nothing;\n    ensures \\result <= a && \\result <= b && \\result <= c;\n    ensures \\result == a || \\result == b || \\result == c;",
        "int minimum_three(int a, int b, int c)",
        "int result = a;\n  if (b < result) result = b;\n  if (c < result) result = c;\n  return result;",
        "return a;",
        ("branch",),
    ),
    scalar_task(
        "clamp-around-zero",
        "three-way-order",
        "zero-clamp",
        "validation",
        "requires lower <= 0 <= upper;\n    assigns \\nothing;\n    ensures lower <= \\result <= upper;\n    ensures x < lower ==> \\result == lower;\n    ensures x > upper ==> \\result == upper;\n    ensures lower <= x <= upper ==> \\result == x;",
        "int clamp_around_zero(int x, int lower, int upper)",
        "if (x < lower) return lower;\n  if (x > upper) return upper;\n  return x;",
        "return 0;",
        ("branch",),
    ),
    scalar_task(
        "conditional-add-subtract",
        "conditional-arithmetic",
        "add-or-subtract",
        "validation",
        "requires -2147483648 <= x + delta <= 2147483647;\n    requires -2147483648 <= x - delta <= 2147483647;\n    assigns \\nothing;\n    ensures condition != 0 ==> \\result == x + delta;\n    ensures condition == 0 ==> \\result == x - delta;",
        "int conditional_add_subtract(int x, int delta, int condition)",
        "if (condition != 0) return x + delta;\n  return x - delta;",
        "return x + delta;",
        ("branch", "overflow"),
    ),
    scalar_task(
        "conditional-step",
        "conditional-arithmetic",
        "increment-or-decrement",
        "validation",
        "requires -2147483647 <= x <= 2147483646;\n    assigns \\nothing;\n    ensures up != 0 ==> \\result == x + 1;\n    ensures up == 0 ==> \\result == x - 1;",
        "int conditional_step(int x, int up)",
        "if (up != 0) return x + 1;\n  return x - 1;",
        "return x;",
        ("branch", "overflow"),
    ),
    scalar_task(
        "conditional-negate",
        "conditional-arithmetic",
        "negate-or-identity",
        "validation",
        "requires x >= -2147483647;\n    assigns \\nothing;\n    ensures negate != 0 ==> \\result == -x;\n    ensures negate == 0 ==> \\result == x;",
        "int conditional_negate(int x, int negate)",
        "if (negate != 0) return -x;\n  return x;",
        "return x;",
        ("branch", "overflow"),
    ),
    scalar_task(
        "conditional-extreme",
        "conditional-arithmetic",
        "minimum-or-maximum",
        "validation",
        "assigns \\nothing;\n    ensures choose_max != 0 ==> \\result >= a && \\result >= b;\n    ensures choose_max == 0 ==> \\result <= a && \\result <= b;\n    ensures \\result == a || \\result == b;",
        "int conditional_extreme(int a, int b, int choose_max)",
        "if (choose_max != 0) { if (a > b) return a; return b; }\n  if (a < b) return a;\n  return b;",
        "return a;",
        ("branch",),
    ),
    scalar_task(
        "add-three-bounded",
        "bounded-composition",
        "sum-three",
        "validation",
        "requires -2147483648 <= a + b <= 2147483647;\n    requires -2147483648 <= a + b + c <= 2147483647;\n    assigns \\nothing;\n    ensures \\result == a + b + c;",
        "int add_three_bounded(int a, int b, int c)",
        "int partial = a + b;\n  return partial + c;",
        "return a + b;",
        ("overflow",),
    ),
    scalar_task(
        "twice-plus-bounded",
        "bounded-composition",
        "twice-plus",
        "validation",
        "requires -2147483648 <= 2 * x <= 2147483647;\n    requires -2147483648 <= 2 * x + y <= 2147483647;\n    assigns \\nothing;\n    ensures \\result == 2 * x + y;",
        "int twice_plus_bounded(int x, int y)",
        "int doubled = 2 * x;\n  return doubled + y;",
        "return x + y;",
        ("overflow",),
    ),
    scalar_task(
        "absolute-difference-bounded",
        "bounded-composition",
        "absolute-difference",
        "validation",
        "requires -2147483647 <= a - b <= 2147483647;\n    assigns \\nothing;\n    ensures \\result >= 0;\n    ensures \\result == a - b || \\result == b - a;",
        "int absolute_difference_bounded(int a, int b)",
        "int difference = a - b;\n  if (difference < 0) return -difference;\n  return difference;",
        "return a - b;",
        ("branch", "overflow"),
    ),
    scalar_task(
        "average-nonnegative",
        "bounded-composition",
        "nonnegative-average",
        "validation",
        "requires 0 <= a <= 1073741823;\n    requires 0 <= b <= 1073741823;\n    assigns \\nothing;\n    ensures \\result == (a + b) / 2;",
        "int average_nonnegative(int a, int b)",
        "return (a + b) / 2;",
        "return a;",
        ("division", "overflow"),
    ),
    # Pointer and array families are isolated in the test split.
    scalar_task(
        "store-value",
        "pointer-mutator",
        "single-store",
        "test",
        "requires \\valid(out);\n    assigns *out;\n    ensures *out == value;",
        "void store_value(int *out, int value)",
        "*out = value;",
        "*out = 0;",
        ("pointer", "assigns"),
    ),
    scalar_task(
        "zero-value",
        "pointer-mutator",
        "single-zero",
        "test",
        "requires \\valid(out);\n    assigns *out;\n    ensures *out == 0;",
        "void zero_value(int *out)",
        "*out = 0;",
        "*out = 1;",
        ("pointer", "assigns"),
    ),
    scalar_task(
        "increment-cell",
        "pointer-mutator",
        "cell-increment",
        "test",
        "requires \\valid(cell);\n    requires *cell <= 2147483646;\n    assigns *cell;\n    ensures *cell == \\old(*cell) + 1;",
        "void increment_cell(int *cell)",
        "*cell = *cell + 1;",
        "*cell = *cell - 1;",
        ("pointer", "assigns", "overflow"),
    ),
    scalar_task(
        "decrement-cell",
        "pointer-mutator",
        "cell-decrement",
        "test",
        "requires \\valid(cell);\n    requires *cell >= -2147483647;\n    assigns *cell;\n    ensures *cell == \\old(*cell) - 1;",
        "void decrement_cell(int *cell)",
        "*cell = *cell - 1;",
        "*cell = *cell + 1;",
        ("pointer", "assigns", "overflow"),
    ),
    scalar_task(
        "copy-separated",
        "pointer-mutator",
        "separated-copy",
        "test",
        "requires \\valid(source) && \\valid(destination);\n    requires \\separated(source, destination);\n    assigns *destination;\n    ensures *destination == \\old(*source);\n    ensures *source == \\old(*source);",
        "void copy_separated(const int *source, int *destination)",
        "*destination = *source;",
        "*destination = 0;",
        ("pointer", "assigns", "separation"),
    ),
    scalar_task(
        "add-to-cell",
        "pointer-mutator",
        "cell-addition",
        "test",
        "requires \\valid(cell);\n    requires -2147483648 <= *cell + delta <= 2147483647;\n    assigns *cell;\n    ensures *cell == \\old(*cell) + delta;",
        "void add_to_cell(int *cell, int delta)",
        "*cell = *cell + delta;",
        "*cell = delta;",
        ("pointer", "assigns", "overflow"),
    ),
    scalar_task(
        "read-first",
        "array-access",
        "first-read",
        "test",
        "requires n > 0;\n    requires \\valid_read(a + (0 .. n - 1));\n    assigns \\nothing;\n    ensures \\result == a[0];",
        "int read_first(const int *a, int n)",
        "return a[0];",
        "return a[n - 1];",
        ("pointer", "array"),
    ),
    scalar_task(
        "read-last",
        "array-access",
        "last-read",
        "test",
        "requires n > 0;\n    requires \\valid_read(a + (0 .. n - 1));\n    assigns \\nothing;\n    ensures \\result == a[n - 1];",
        "int read_last(const int *a, int n)",
        "return a[n - 1];",
        "return a[0];",
        ("pointer", "array"),
    ),
    scalar_task(
        "sum-array-ends",
        "array-access",
        "ends-sum",
        "test",
        "requires n > 0;\n    requires \\valid_read(a + (0 .. n - 1));\n    requires -2147483648 <= a[0] + a[n - 1] <= 2147483647;\n    assigns \\nothing;\n    ensures \\result == a[0] + a[n - 1];",
        "int sum_array_ends(const int *a, int n)",
        "return a[0] + a[n - 1];",
        "return a[0];",
        ("pointer", "array", "overflow"),
    ),
    scalar_task(
        "set-array-first",
        "array-access",
        "first-write",
        "test",
        "requires n > 0;\n    requires \\valid(a + (0 .. n - 1));\n    assigns a[0];\n    ensures a[0] == value;",
        "void set_array_first(int *a, int n, int value)",
        "a[0] = value;",
        "a[n - 1] = value;",
        ("pointer", "array", "assigns"),
    ),
    scalar_task(
        "set-array-last",
        "array-access",
        "last-write",
        "test",
        "requires n > 0;\n    requires \\valid(a + (0 .. n - 1));\n    assigns a[n - 1];\n    ensures a[n - 1] == value;",
        "void set_array_last(int *a, int n, int value)",
        "a[n - 1] = value;",
        "a[0] = value;",
        ("pointer", "array", "assigns"),
    ),
    scalar_task(
        "set-array-ends",
        "array-access",
        "ends-write",
        "test",
        "requires n > 1;\n    requires \\valid(a + (0 .. n - 1));\n    assigns a[0], a[n - 1];\n    ensures a[0] == first;\n    ensures a[n - 1] == last;",
        "void set_array_ends(int *a, int n, int first, int last)",
        "a[0] = first;\n  a[n - 1] = last;",
        "a[0] = last;\n  a[n - 1] = first;",
        ("pointer", "array", "assigns"),
    ),
)

TASKS = BASE_TASKS + EXTRA_TASKS
assert len(TASKS) == 64


def normalized_sha256(source: str) -> str:
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def make_record(task: DraftTask) -> dict:
    if BODY_TOKEN not in task.template:
        raise ValueError(f"missing body token: {task.slug}")
    reference = task.template.replace(BODY_TOKEN, task.body)
    skeleton = task.template.replace(BODY_TOKEN, "// TODO: complete")
    negative = task.template.replace(BODY_TOKEN, task.wrong_body)
    return {
        "stable_id": f"acslc:core-v1:{task.slug}",
        "dataset_id": "core-v1",
        "dataset_version": "0.1.4",
        "source_kind": "project-authored",
        "source_repository_url": "https://github.com/stanleyngugi/formally-verified-code-rl",
        "source_revision": "v0.1.4",
        "source_path": f"environments/acsl-c/scripts/build_core_v1.py#{task.slug}",
        "source_content_sha256": normalized_sha256(reference),
        "license_spdx": "Apache-2.0",
        "copyright_notice": "Copyright 2026 verified-rl-envs contributors",
        "transformation_description": "Target function body replaced by a TODO marker",
        "semantic_family": task.semantic_family,
        "derivation_family": task.derivation_family,
        "review_status": "machine-reviewed-and-verified",
        "mode": "hints",
        "problem": "",
        "skeleton_c": skeleton,
        "reference_solution": reference,
        "negative_cases": [
            {
                "name": "wrong-semantics",
                "candidate_source": negative,
                "expected": "verification-failure",
            }
        ],
        "features": list(task.features),
        "vc_estimate": 0,
        "difficulty_bucket": "unmeasured",
        "has_spectests": False,
        "spectests": None,
        "non_vacuous": True,
        "data_schema_version": 2,
        "provenance": f"project:core-v1:{task.slug}",
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = [make_record(task) for task in TASKS]
    task_path = OUTPUT / "tasks.jsonl"
    task_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    splits = {name: [] for name in ("train", "validation", "test")}
    for task in TASKS:
        splits[task.split].append(f"acslc:core-v1:{task.slug}")
    manifest = {
        "schema_version": 1,
        "dataset_id": "core-v1",
        "dataset_version": "0.1.4",
        "status": "core-64-machine-reviewed-and-verified",
        "split_policy": "semantic and derivation families remain within one split",
        "splits": splits,
        "counts": {name: len(ids) for name, ids in splits.items()},
        "task_file_sha256": normalized_sha256(task_path.read_text(encoding="utf-8")),
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
