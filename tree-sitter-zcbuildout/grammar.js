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
        seq(
          $._section_header,
          /[\n]+/,
          repeat(choice(seq($.option, /[\n]+/), $.comment))
        )
      ),

    _section_header: ($) =>
      seq("[", $.section_name, optional(seq(/:/, $.section_condition)), "]"),
    section_name: ($) => /[^\[\]:\n]+/,
    section_condition: ($) => /[^\[\]\n]+/,

    // TODO: multi line options
    option: ($) => seq($.option_name, "=", $.option_value),

    option_name: ($) => /[^#=\s\[]+/,
    option_value: ($) =>
      seq(
        optional($.option_text),
        repeat1(seq($.option_with_reference, optional($.option_text)))
      ),

    option_with_reference: ($) =>
      seq("${", optional($.referenced_section), ":", $.referenced_option, "}"),
    referenced_section: ($) => /[^:\}\n]+/,
    referenced_option: ($) => /[^\n\}]+/,
    option_text: ($) => choice(/[^\$\n]+[^\n]*/, /[^\$\n]\$\{[^\}\n]+/),

    comment: ($) => token(prec(-10, /#.*\n+/)),
  },
});
