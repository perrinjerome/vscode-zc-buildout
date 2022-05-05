module.exports = grammar({
  name: "zcbuildout",

  extras: ($) => [
    /[ \t]+\n*/, // Ignore empty lines.
  ],
  conflicts: ($) => [
    // [$.option_value]
  ],
  rules: {
    profile: ($) =>
      seq(/[\n]*/, optional(repeat($.comment)), repeat(seq($.section))),

    section: ($) =>
      prec.left(
        seq($._section_header, /[\n]+/, repeat(choice($.option, $.comment)))
      ),

    _section_header: ($) =>
      seq("[", $.section_name, optional(seq(/:/, $.section_condition)), "]"),
    section_name: ($) => /[^\[\]:\n]+/,
    section_condition: ($) => /[^\[\]\n]+/,

    option: ($) => seq($.option_name, "=", $.option_value),

    option_name: ($) => /[^#;=\s\[]+/,
    option_value: ($) =>
      choice(
        seq(
          $._option_value_mono_line,
          prec.left(1, repeat($._option_value_multi_line))
        ),
        seq(/\n/, prec.left(2, repeat1($._option_value_multi_line)))
      ),
    _option_value_mono_line: ($) => prec.left(1, seq($.option_text, /\n+/)),
    _option_value_multi_line: ($) =>
      prec.left(2, repeat1(seq(/\s+/, $.option_text, /\n+/))),

    option_text: ($) => /[^\n]+/,
    xoption_value: ($) =>
      seq(
        optional($.option_text),
        repeat1(seq($.option_with_reference, optional($.option_text)))
      ),

    // option = text maybe ${ok:ok}
    option_with_reference: ($) =>
      seq("${", optional($.referenced_section), ":", $.referenced_option, "}"),
    referenced_section: ($) => /[^:\}\n]+/,
    referenced_option: ($) => /[^\n\}]+/,
    xoption_text: ($) => choice(/[^\$\n]+[^\n]*/, /[^\$\n]\$\{[^\}\n]+/),

    comment: ($) => token(prec(-10, /[#;]+.*\n+/)),
  },
});
