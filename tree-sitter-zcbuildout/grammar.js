module.exports = grammar({
  name: "zcbuildout",

  extras: ($) => [
    /[ \t]+\n*/, // Ignore empty lines.
  ],

  rules: {
    profile: ($) =>
      seq(/[\n]*/, optional(repeat($.comment)), repeat(seq($.section))),

    section: ($) =>
      prec.left(
        seq($._section_header, /[\n]+/, repeat(choice($.option, $.comment)))
      ),

    _section_header: ($) =>
      seq(
        "[",
        field("section_name", $.section_name),
        optional(seq(/:/, field("section_condition", $.section_condition))),
        "]"
      ),
    section_name: ($) => /[^\[\]:\n]+/,
    section_condition: ($) => /[^\[\]\n]+/,

    option: ($) => seq($.option_name, "=", /\s*/, $.option_value),

    option_name: ($) => /[^#;=\s\[]+/,
    option_value: ($) =>
      choice(
        seq(
          $._option_value_mono_line,
          prec.left(1, repeat($._option_value_multi_line))
        ),
        seq(/\n/, prec.left(2, repeat1($._option_value_multi_line)))
      ),
    _option_value_mono_line: ($) => prec.left(1, seq($._option_text, /\n+/)),
    _option_value_multi_line: ($) =>
      prec.left(2, repeat1(seq(/\s+/, $._option_text, /\n+/))),

    _option_text: ($) =>
      repeat1(choice($.option_text, $.option_with_reference)),
    option_text: ($) => /([^\n]+\$\$[^\n]*|[^\n]*\$\$[^\n]+|[^\$\n]+)+/,

    option_with_reference: ($) =>
      seq(
        "${",
        field("referenced_section", optional($.referenced_section)),
        ":",
        field("referenced_option", $.referenced_option),
        "}"
      ),
    referenced_section: ($) => /[^:\}\n]+/,
    referenced_option: ($) => /[^\n\}]+/,

    comment: ($) => token(prec(-10, /[#;]+.*\n+/)),
  },
});
