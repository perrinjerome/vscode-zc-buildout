module.exports = grammar({
  name: "zcbuildout",

  extras: ($) => [
    // $.comment,
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

    option: ($) => seq($.option_name, "=", $.option_value),

    option_name: ($) => /[^#=\s\[]+/,
    option_value: ($) => /[^\n]+/,

    comment: ($) => token(prec(-10, /#.*\n+/)),
  },
});
