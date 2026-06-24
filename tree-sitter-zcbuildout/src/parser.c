#include <tree_sitter/parser.h>

#if defined(__GNUC__) || defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#endif

#define LANGUAGE_VERSION 13
#define STATE_COUNT 43
#define LARGE_STATE_COUNT 2
#define SYMBOL_COUNT 35
#define ALIAS_COUNT 0
#define TOKEN_COUNT 21
#define EXTERNAL_TOKEN_COUNT 0
#define FIELD_COUNT 4
#define MAX_ALIAS_SEQUENCE_LENGTH 5
#define PRODUCTION_ID_COUNT 6

enum {
  aux_sym_profile_token1 = 1,
  aux_sym_section_token1 = 2,
  anon_sym_LBRACK = 3,
  aux_sym__section_header_token1 = 4,
  anon_sym_RBRACK = 5,
  sym_section_name = 6,
  sym_section_condition = 7,
  anon_sym_EQ = 8,
  aux_sym_option_token1 = 9,
  sym_option_name = 10,
  aux_sym_option_value_token1 = 11,
  aux_sym__option_value_mono_line_token1 = 12,
  aux_sym__option_value_multi_line_token1 = 13,
  sym_option_text = 14,
  anon_sym_DOLLAR_LBRACE = 15,
  anon_sym_COLON = 16,
  anon_sym_RBRACE = 17,
  sym_referenced_section = 18,
  sym_referenced_option = 19,
  sym_comment = 20,
  sym_profile = 21,
  sym_section = 22,
  sym__section_header = 23,
  sym_option = 24,
  sym_option_value = 25,
  sym__option_value_mono_line = 26,
  sym__option_value_multi_line = 27,
  aux_sym__option_text = 28,
  sym_option_with_reference = 29,
  aux_sym_profile_repeat1 = 30,
  aux_sym_profile_repeat2 = 31,
  aux_sym_section_repeat1 = 32,
  aux_sym_option_value_repeat1 = 33,
  aux_sym__option_value_multi_line_repeat1 = 34,
};

static const char * const ts_symbol_names[] = {
  [ts_builtin_sym_end] = "end",
  [aux_sym_profile_token1] = "profile_token1",
  [aux_sym_section_token1] = "section_token1",
  [anon_sym_LBRACK] = "[",
  [aux_sym__section_header_token1] = "_section_header_token1",
  [anon_sym_RBRACK] = "]",
  [sym_section_name] = "section_name",
  [sym_section_condition] = "section_condition",
  [anon_sym_EQ] = "=",
  [aux_sym_option_token1] = "option_token1",
  [sym_option_name] = "option_name",
  [aux_sym_option_value_token1] = "option_value_token1",
  [aux_sym__option_value_mono_line_token1] = "_option_value_mono_line_token1",
  [aux_sym__option_value_multi_line_token1] = "_option_value_multi_line_token1",
  [sym_option_text] = "option_text",
  [anon_sym_DOLLAR_LBRACE] = "${",
  [anon_sym_COLON] = ":",
  [anon_sym_RBRACE] = "}",
  [sym_referenced_section] = "referenced_section",
  [sym_referenced_option] = "referenced_option",
  [sym_comment] = "comment",
  [sym_profile] = "profile",
  [sym_section] = "section",
  [sym__section_header] = "_section_header",
  [sym_option] = "option",
  [sym_option_value] = "option_value",
  [sym__option_value_mono_line] = "_option_value_mono_line",
  [sym__option_value_multi_line] = "_option_value_multi_line",
  [aux_sym__option_text] = "_option_text",
  [sym_option_with_reference] = "option_with_reference",
  [aux_sym_profile_repeat1] = "profile_repeat1",
  [aux_sym_profile_repeat2] = "profile_repeat2",
  [aux_sym_section_repeat1] = "section_repeat1",
  [aux_sym_option_value_repeat1] = "option_value_repeat1",
  [aux_sym__option_value_multi_line_repeat1] = "_option_value_multi_line_repeat1",
};

static const TSSymbol ts_symbol_map[] = {
  [ts_builtin_sym_end] = ts_builtin_sym_end,
  [aux_sym_profile_token1] = aux_sym_profile_token1,
  [aux_sym_section_token1] = aux_sym_section_token1,
  [anon_sym_LBRACK] = anon_sym_LBRACK,
  [aux_sym__section_header_token1] = aux_sym__section_header_token1,
  [anon_sym_RBRACK] = anon_sym_RBRACK,
  [sym_section_name] = sym_section_name,
  [sym_section_condition] = sym_section_condition,
  [anon_sym_EQ] = anon_sym_EQ,
  [aux_sym_option_token1] = aux_sym_option_token1,
  [sym_option_name] = sym_option_name,
  [aux_sym_option_value_token1] = aux_sym_option_value_token1,
  [aux_sym__option_value_mono_line_token1] = aux_sym__option_value_mono_line_token1,
  [aux_sym__option_value_multi_line_token1] = aux_sym__option_value_multi_line_token1,
  [sym_option_text] = sym_option_text,
  [anon_sym_DOLLAR_LBRACE] = anon_sym_DOLLAR_LBRACE,
  [anon_sym_COLON] = anon_sym_COLON,
  [anon_sym_RBRACE] = anon_sym_RBRACE,
  [sym_referenced_section] = sym_referenced_section,
  [sym_referenced_option] = sym_referenced_option,
  [sym_comment] = sym_comment,
  [sym_profile] = sym_profile,
  [sym_section] = sym_section,
  [sym__section_header] = sym__section_header,
  [sym_option] = sym_option,
  [sym_option_value] = sym_option_value,
  [sym__option_value_mono_line] = sym__option_value_mono_line,
  [sym__option_value_multi_line] = sym__option_value_multi_line,
  [aux_sym__option_text] = aux_sym__option_text,
  [sym_option_with_reference] = sym_option_with_reference,
  [aux_sym_profile_repeat1] = aux_sym_profile_repeat1,
  [aux_sym_profile_repeat2] = aux_sym_profile_repeat2,
  [aux_sym_section_repeat1] = aux_sym_section_repeat1,
  [aux_sym_option_value_repeat1] = aux_sym_option_value_repeat1,
  [aux_sym__option_value_multi_line_repeat1] = aux_sym__option_value_multi_line_repeat1,
};

static const TSSymbolMetadata ts_symbol_metadata[] = {
  [ts_builtin_sym_end] = {
    .visible = false,
    .named = true,
  },
  [aux_sym_profile_token1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym_section_token1] = {
    .visible = false,
    .named = false,
  },
  [anon_sym_LBRACK] = {
    .visible = true,
    .named = false,
  },
  [aux_sym__section_header_token1] = {
    .visible = false,
    .named = false,
  },
  [anon_sym_RBRACK] = {
    .visible = true,
    .named = false,
  },
  [sym_section_name] = {
    .visible = true,
    .named = true,
  },
  [sym_section_condition] = {
    .visible = true,
    .named = true,
  },
  [anon_sym_EQ] = {
    .visible = true,
    .named = false,
  },
  [aux_sym_option_token1] = {
    .visible = false,
    .named = false,
  },
  [sym_option_name] = {
    .visible = true,
    .named = true,
  },
  [aux_sym_option_value_token1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym__option_value_mono_line_token1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym__option_value_multi_line_token1] = {
    .visible = false,
    .named = false,
  },
  [sym_option_text] = {
    .visible = true,
    .named = true,
  },
  [anon_sym_DOLLAR_LBRACE] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_COLON] = {
    .visible = true,
    .named = false,
  },
  [anon_sym_RBRACE] = {
    .visible = true,
    .named = false,
  },
  [sym_referenced_section] = {
    .visible = true,
    .named = true,
  },
  [sym_referenced_option] = {
    .visible = true,
    .named = true,
  },
  [sym_comment] = {
    .visible = true,
    .named = true,
  },
  [sym_profile] = {
    .visible = true,
    .named = true,
  },
  [sym_section] = {
    .visible = true,
    .named = true,
  },
  [sym__section_header] = {
    .visible = false,
    .named = true,
  },
  [sym_option] = {
    .visible = true,
    .named = true,
  },
  [sym_option_value] = {
    .visible = true,
    .named = true,
  },
  [sym__option_value_mono_line] = {
    .visible = false,
    .named = true,
  },
  [sym__option_value_multi_line] = {
    .visible = false,
    .named = true,
  },
  [aux_sym__option_text] = {
    .visible = false,
    .named = false,
  },
  [sym_option_with_reference] = {
    .visible = true,
    .named = true,
  },
  [aux_sym_profile_repeat1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym_profile_repeat2] = {
    .visible = false,
    .named = false,
  },
  [aux_sym_section_repeat1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym_option_value_repeat1] = {
    .visible = false,
    .named = false,
  },
  [aux_sym__option_value_multi_line_repeat1] = {
    .visible = false,
    .named = false,
  },
};

enum {
  field_referenced_option = 1,
  field_referenced_section = 2,
  field_section_condition = 3,
  field_section_name = 4,
};

static const char * const ts_field_names[] = {
  [0] = NULL,
  [field_referenced_option] = "referenced_option",
  [field_referenced_section] = "referenced_section",
  [field_section_condition] = "section_condition",
  [field_section_name] = "section_name",
};

static const TSFieldMapSlice ts_field_map_slices[PRODUCTION_ID_COUNT] = {
  [1] = {.index = 0, .length = 2},
  [2] = {.index = 2, .length = 1},
  [3] = {.index = 3, .length = 2},
  [4] = {.index = 5, .length = 1},
  [5] = {.index = 6, .length = 2},
};

static const TSFieldMapEntry ts_field_map_entries[] = {
  [0] =
    {field_section_condition, 0, .inherited = true},
    {field_section_name, 0, .inherited = true},
  [2] =
    {field_section_name, 1},
  [3] =
    {field_section_condition, 3},
    {field_section_name, 1},
  [5] =
    {field_referenced_option, 2},
  [6] =
    {field_referenced_option, 3},
    {field_referenced_section, 1},
};

static const TSSymbol ts_alias_sequences[PRODUCTION_ID_COUNT][MAX_ALIAS_SEQUENCE_LENGTH] = {
  [0] = {0},
};

static const uint16_t ts_non_terminal_alias_map[] = {
  0,
};

static bool ts_lex(TSLexer *lexer, TSStateId state) {
  START_LEXER();
  eof = lexer->eof(lexer);
  switch (state) {
    case 0:
      if (eof) ADVANCE(25);
      if (lookahead == '$') ADVANCE(17);
      if (lookahead == ':') ADVANCE(53);
      if (lookahead == '=') ADVANCE(35);
      if (lookahead == '[') ADVANCE(28);
      if (lookahead == ']') ADVANCE(30);
      if (lookahead == '}') ADVANCE(54);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(21)
      if (lookahead == '#' ||
          lookahead == ';') ADVANCE(1);
      END_STATE();
    case 1:
      if (lookahead == '\n') ADVANCE(59);
      if (lookahead == '#' ||
          lookahead == ';') ADVANCE(1);
      if (lookahead != 0) ADVANCE(2);
      END_STATE();
    case 2:
      if (lookahead == '\n') ADVANCE(59);
      if (lookahead != 0) ADVANCE(2);
      END_STATE();
    case 3:
      if (lookahead == '\n') ADVANCE(40);
      if (lookahead == '$') ADVANCE(9);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(46);
      if (lookahead != 0) ADVANCE(50);
      END_STATE();
    case 4:
      if (lookahead == '\n') ADVANCE(42);
      if (lookahead == '$') ADVANCE(9);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(47);
      if (lookahead != 0) ADVANCE(50);
      END_STATE();
    case 5:
      if (lookahead == '\n') SKIP(5)
      if (lookahead == ':') ADVANCE(29);
      if (lookahead == ']') ADVANCE(30);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(5)
      END_STATE();
    case 6:
      if (lookahead == '\n') ADVANCE(27);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(6)
      END_STATE();
    case 7:
      if (lookahead == '\n') SKIP(7)
      if (lookahead == ':') ADVANCE(53);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(7)
      END_STATE();
    case 8:
      if (lookahead == '$') ADVANCE(9);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(48);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(50);
      END_STATE();
    case 9:
      if (lookahead == '$') ADVANCE(11);
      if (lookahead == '{') ADVANCE(52);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(13);
      END_STATE();
    case 10:
      if (lookahead == '$') ADVANCE(49);
      if (lookahead == '{') ADVANCE(52);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(13);
      END_STATE();
    case 11:
      if (lookahead == '$') ADVANCE(49);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(49);
      END_STATE();
    case 12:
      if (lookahead == '$') ADVANCE(49);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(13);
      END_STATE();
    case 13:
      if (lookahead == '$') ADVANCE(12);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(13);
      END_STATE();
    case 14:
      if (lookahead == ':') ADVANCE(53);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(55);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '}') ADVANCE(56);
      END_STATE();
    case 15:
      if (lookahead == ':') ADVANCE(53);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(7)
      END_STATE();
    case 16:
      if (lookahead == ':') ADVANCE(29);
      if (lookahead == ']') ADVANCE(30);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(5)
      END_STATE();
    case 17:
      if (lookahead == '{') ADVANCE(51);
      END_STATE();
    case 18:
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(57);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '}') ADVANCE(58);
      END_STATE();
    case 19:
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(33);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '[' &&
          lookahead != ']') ADVANCE(34);
      END_STATE();
    case 20:
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(31);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != ':' &&
          lookahead != '[' &&
          lookahead != ']') ADVANCE(32);
      END_STATE();
    case 21:
      if (eof) ADVANCE(25);
      if (lookahead == '\n') SKIP(21)
      if (lookahead == '$') ADVANCE(17);
      if (lookahead == ':') ADVANCE(53);
      if (lookahead == '=') ADVANCE(35);
      if (lookahead == '[') ADVANCE(28);
      if (lookahead == ']') ADVANCE(30);
      if (lookahead == '}') ADVANCE(54);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(21)
      if (lookahead == '#' ||
          lookahead == ';') ADVANCE(1);
      END_STATE();
    case 22:
      if (eof) ADVANCE(25);
      if (lookahead == '\n') SKIP(22)
      if (lookahead == '[') ADVANCE(28);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(22)
      if (lookahead == '#' ||
          lookahead == ';') ADVANCE(1);
      if (lookahead != 0 &&
          lookahead != '\r' &&
          lookahead != '=') ADVANCE(39);
      END_STATE();
    case 23:
      if (eof) ADVANCE(25);
      if (lookahead == '[') ADVANCE(28);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(44);
      if (lookahead == '\n' ||
          lookahead == '\r') ADVANCE(45);
      if (lookahead == '#' ||
          lookahead == ';') ADVANCE(1);
      if (lookahead != 0 &&
          lookahead != '=') ADVANCE(39);
      END_STATE();
    case 24:
      if (eof) ADVANCE(25);
      if (lookahead == '[') ADVANCE(28);
      if (lookahead == '\t' ||
          lookahead == ' ') SKIP(22)
      if (lookahead == '#' ||
          lookahead == ';') ADVANCE(1);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '\r' &&
          lookahead != '=') ADVANCE(39);
      END_STATE();
    case 25:
      ACCEPT_TOKEN(ts_builtin_sym_end);
      END_STATE();
    case 26:
      ACCEPT_TOKEN(aux_sym_profile_token1);
      if (lookahead == '\n') ADVANCE(26);
      END_STATE();
    case 27:
      ACCEPT_TOKEN(aux_sym_section_token1);
      if (lookahead == '\n') ADVANCE(27);
      END_STATE();
    case 28:
      ACCEPT_TOKEN(anon_sym_LBRACK);
      END_STATE();
    case 29:
      ACCEPT_TOKEN(aux_sym__section_header_token1);
      END_STATE();
    case 30:
      ACCEPT_TOKEN(anon_sym_RBRACK);
      END_STATE();
    case 31:
      ACCEPT_TOKEN(sym_section_name);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(31);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != ':' &&
          lookahead != '[' &&
          lookahead != ']') ADVANCE(32);
      END_STATE();
    case 32:
      ACCEPT_TOKEN(sym_section_name);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != ':' &&
          lookahead != '[' &&
          lookahead != ']') ADVANCE(32);
      END_STATE();
    case 33:
      ACCEPT_TOKEN(sym_section_condition);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(33);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '[' &&
          lookahead != ']') ADVANCE(34);
      END_STATE();
    case 34:
      ACCEPT_TOKEN(sym_section_condition);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '[' &&
          lookahead != ']') ADVANCE(34);
      END_STATE();
    case 35:
      ACCEPT_TOKEN(anon_sym_EQ);
      END_STATE();
    case 36:
      ACCEPT_TOKEN(aux_sym_option_token1);
      if (lookahead == '\n') ADVANCE(36);
      if (lookahead == '\r') ADVANCE(38);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(36);
      END_STATE();
    case 37:
      ACCEPT_TOKEN(aux_sym_option_token1);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(36);
      if (lookahead == '\n' ||
          lookahead == '\r') ADVANCE(38);
      END_STATE();
    case 38:
      ACCEPT_TOKEN(aux_sym_option_token1);
      if (lookahead == '\t' ||
          lookahead == '\n' ||
          lookahead == '\r' ||
          lookahead == ' ') ADVANCE(38);
      END_STATE();
    case 39:
      ACCEPT_TOKEN(sym_option_name);
      if (lookahead != 0 &&
          lookahead != '\t' &&
          lookahead != '\n' &&
          lookahead != '\r' &&
          lookahead != ' ' &&
          lookahead != '#' &&
          lookahead != ';' &&
          lookahead != '=' &&
          lookahead != '[') ADVANCE(39);
      END_STATE();
    case 40:
      ACCEPT_TOKEN(aux_sym_option_value_token1);
      END_STATE();
    case 41:
      ACCEPT_TOKEN(aux_sym_option_value_token1);
      if (lookahead == '\n') ADVANCE(41);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(46);
      END_STATE();
    case 42:
      ACCEPT_TOKEN(aux_sym__option_value_mono_line_token1);
      if (lookahead == '\n') ADVANCE(42);
      END_STATE();
    case 43:
      ACCEPT_TOKEN(aux_sym__option_value_mono_line_token1);
      if (lookahead == '\n') ADVANCE(43);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(47);
      END_STATE();
    case 44:
      ACCEPT_TOKEN(aux_sym__option_value_multi_line_token1);
      if (lookahead == '\n') ADVANCE(44);
      if (lookahead == '\r') ADVANCE(45);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(44);
      END_STATE();
    case 45:
      ACCEPT_TOKEN(aux_sym__option_value_multi_line_token1);
      if (lookahead == '\t' ||
          lookahead == '\n' ||
          lookahead == '\r' ||
          lookahead == ' ') ADVANCE(45);
      END_STATE();
    case 46:
      ACCEPT_TOKEN(sym_option_text);
      if (lookahead == '\n') ADVANCE(41);
      if (lookahead == '$') ADVANCE(10);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(46);
      if (lookahead != 0) ADVANCE(50);
      END_STATE();
    case 47:
      ACCEPT_TOKEN(sym_option_text);
      if (lookahead == '\n') ADVANCE(43);
      if (lookahead == '$') ADVANCE(10);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(47);
      if (lookahead != 0) ADVANCE(50);
      END_STATE();
    case 48:
      ACCEPT_TOKEN(sym_option_text);
      if (lookahead == '$') ADVANCE(10);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(48);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(50);
      END_STATE();
    case 49:
      ACCEPT_TOKEN(sym_option_text);
      if (lookahead == '$') ADVANCE(49);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(49);
      END_STATE();
    case 50:
      ACCEPT_TOKEN(sym_option_text);
      if (lookahead == '$') ADVANCE(12);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(50);
      END_STATE();
    case 51:
      ACCEPT_TOKEN(anon_sym_DOLLAR_LBRACE);
      END_STATE();
    case 52:
      ACCEPT_TOKEN(anon_sym_DOLLAR_LBRACE);
      if (lookahead == '$') ADVANCE(12);
      if (lookahead != 0 &&
          lookahead != '\n') ADVANCE(13);
      END_STATE();
    case 53:
      ACCEPT_TOKEN(anon_sym_COLON);
      END_STATE();
    case 54:
      ACCEPT_TOKEN(anon_sym_RBRACE);
      END_STATE();
    case 55:
      ACCEPT_TOKEN(sym_referenced_section);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(55);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != ':' &&
          lookahead != '}') ADVANCE(56);
      END_STATE();
    case 56:
      ACCEPT_TOKEN(sym_referenced_section);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != ':' &&
          lookahead != '}') ADVANCE(56);
      END_STATE();
    case 57:
      ACCEPT_TOKEN(sym_referenced_option);
      if (lookahead == '\t' ||
          lookahead == ' ') ADVANCE(57);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '}') ADVANCE(58);
      END_STATE();
    case 58:
      ACCEPT_TOKEN(sym_referenced_option);
      if (lookahead != 0 &&
          lookahead != '\n' &&
          lookahead != '}') ADVANCE(58);
      END_STATE();
    case 59:
      ACCEPT_TOKEN(sym_comment);
      if (lookahead == '\n') ADVANCE(59);
      END_STATE();
    default:
      return false;
  }
}

static const TSLexMode ts_lex_modes[STATE_COUNT] = {
  [0] = {.lex_state = 0},
  [1] = {.lex_state = 26},
  [2] = {.lex_state = 23},
  [3] = {.lex_state = 23},
  [4] = {.lex_state = 23},
  [5] = {.lex_state = 23},
  [6] = {.lex_state = 3},
  [7] = {.lex_state = 0},
  [8] = {.lex_state = 0},
  [9] = {.lex_state = 23},
  [10] = {.lex_state = 24},
  [11] = {.lex_state = 24},
  [12] = {.lex_state = 24},
  [13] = {.lex_state = 4},
  [14] = {.lex_state = 0},
  [15] = {.lex_state = 4},
  [16] = {.lex_state = 0},
  [17] = {.lex_state = 0},
  [18] = {.lex_state = 23},
  [19] = {.lex_state = 23},
  [20] = {.lex_state = 4},
  [21] = {.lex_state = 0},
  [22] = {.lex_state = 23},
  [23] = {.lex_state = 24},
  [24] = {.lex_state = 8},
  [25] = {.lex_state = 4},
  [26] = {.lex_state = 4},
  [27] = {.lex_state = 16},
  [28] = {.lex_state = 14},
  [29] = {.lex_state = 6},
  [30] = {.lex_state = 15},
  [31] = {.lex_state = 18},
  [32] = {.lex_state = 0},
  [33] = {.lex_state = 37},
  [34] = {.lex_state = 0},
  [35] = {.lex_state = 0},
  [36] = {.lex_state = 6},
  [37] = {.lex_state = 0},
  [38] = {.lex_state = 18},
  [39] = {.lex_state = 19},
  [40] = {.lex_state = 6},
  [41] = {.lex_state = 0},
  [42] = {.lex_state = 20},
};

static const uint16_t ts_parse_table[LARGE_STATE_COUNT][SYMBOL_COUNT] = {
  [0] = {
    [ts_builtin_sym_end] = ACTIONS(1),
    [anon_sym_LBRACK] = ACTIONS(1),
    [aux_sym__section_header_token1] = ACTIONS(1),
    [anon_sym_RBRACK] = ACTIONS(1),
    [anon_sym_EQ] = ACTIONS(1),
    [anon_sym_DOLLAR_LBRACE] = ACTIONS(1),
    [anon_sym_COLON] = ACTIONS(1),
    [anon_sym_RBRACE] = ACTIONS(1),
    [sym_comment] = ACTIONS(1),
  },
  [1] = {
    [sym_profile] = STATE(32),
    [aux_sym_profile_token1] = ACTIONS(3),
  },
};

static const uint16_t ts_small_parse_table[] = {
  [0] = 4,
    ACTIONS(5), 1,
      ts_builtin_sym_end,
    ACTIONS(9), 1,
      aux_sym__option_value_multi_line_token1,
    ACTIONS(7), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
    STATE(2), 3,
      sym__option_value_multi_line,
      aux_sym_option_value_repeat1,
      aux_sym__option_value_multi_line_repeat1,
  [17] = 4,
    ACTIONS(12), 1,
      ts_builtin_sym_end,
    ACTIONS(16), 1,
      aux_sym__option_value_multi_line_token1,
    ACTIONS(14), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
    STATE(2), 3,
      sym__option_value_multi_line,
      aux_sym_option_value_repeat1,
      aux_sym__option_value_multi_line_repeat1,
  [34] = 4,
    ACTIONS(16), 1,
      aux_sym__option_value_multi_line_token1,
    ACTIONS(18), 1,
      ts_builtin_sym_end,
    ACTIONS(20), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
    STATE(5), 3,
      sym__option_value_multi_line,
      aux_sym_option_value_repeat1,
      aux_sym__option_value_multi_line_repeat1,
  [51] = 4,
    ACTIONS(12), 1,
      ts_builtin_sym_end,
    ACTIONS(16), 1,
      aux_sym__option_value_multi_line_token1,
    ACTIONS(14), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
    STATE(2), 3,
      sym__option_value_multi_line,
      aux_sym_option_value_repeat1,
      aux_sym__option_value_multi_line_repeat1,
  [68] = 6,
    ACTIONS(22), 1,
      aux_sym_option_value_token1,
    ACTIONS(24), 1,
      sym_option_text,
    ACTIONS(26), 1,
      anon_sym_DOLLAR_LBRACE,
    STATE(4), 1,
      sym__option_value_mono_line,
    STATE(23), 1,
      sym_option_value,
    STATE(20), 2,
      aux_sym__option_text,
      sym_option_with_reference,
  [88] = 6,
    ACTIONS(28), 1,
      ts_builtin_sym_end,
    ACTIONS(30), 1,
      anon_sym_LBRACK,
    ACTIONS(32), 1,
      sym_comment,
    STATE(8), 1,
      aux_sym_profile_repeat1,
    STATE(40), 1,
      sym__section_header,
    STATE(14), 2,
      sym_section,
      aux_sym_profile_repeat2,
  [108] = 6,
    ACTIONS(30), 1,
      anon_sym_LBRACK,
    ACTIONS(34), 1,
      ts_builtin_sym_end,
    ACTIONS(36), 1,
      sym_comment,
    STATE(21), 1,
      aux_sym_profile_repeat1,
    STATE(40), 1,
      sym__section_header,
    STATE(17), 2,
      sym_section,
      aux_sym_profile_repeat2,
  [128] = 4,
    ACTIONS(38), 1,
      ts_builtin_sym_end,
    ACTIONS(42), 1,
      aux_sym__option_value_multi_line_token1,
    STATE(9), 1,
      aux_sym__option_value_multi_line_repeat1,
    ACTIONS(40), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
  [143] = 4,
    ACTIONS(47), 1,
      sym_option_name,
    ACTIONS(50), 1,
      sym_comment,
    ACTIONS(45), 2,
      ts_builtin_sym_end,
      anon_sym_LBRACK,
    STATE(10), 2,
      sym_option,
      aux_sym_section_repeat1,
  [158] = 4,
    ACTIONS(55), 1,
      sym_option_name,
    ACTIONS(57), 1,
      sym_comment,
    ACTIONS(53), 2,
      ts_builtin_sym_end,
      anon_sym_LBRACK,
    STATE(12), 2,
      sym_option,
      aux_sym_section_repeat1,
  [173] = 4,
    ACTIONS(55), 1,
      sym_option_name,
    ACTIONS(61), 1,
      sym_comment,
    ACTIONS(59), 2,
      ts_builtin_sym_end,
      anon_sym_LBRACK,
    STATE(10), 2,
      sym_option,
      aux_sym_section_repeat1,
  [188] = 4,
    ACTIONS(63), 1,
      aux_sym__option_value_mono_line_token1,
    ACTIONS(65), 1,
      sym_option_text,
    ACTIONS(68), 1,
      anon_sym_DOLLAR_LBRACE,
    STATE(13), 2,
      aux_sym__option_text,
      sym_option_with_reference,
  [202] = 4,
    ACTIONS(30), 1,
      anon_sym_LBRACK,
    ACTIONS(34), 1,
      ts_builtin_sym_end,
    STATE(40), 1,
      sym__section_header,
    STATE(16), 2,
      sym_section,
      aux_sym_profile_repeat2,
  [216] = 4,
    ACTIONS(26), 1,
      anon_sym_DOLLAR_LBRACE,
    ACTIONS(71), 1,
      aux_sym__option_value_mono_line_token1,
    ACTIONS(73), 1,
      sym_option_text,
    STATE(13), 2,
      aux_sym__option_text,
      sym_option_with_reference,
  [230] = 4,
    ACTIONS(75), 1,
      ts_builtin_sym_end,
    ACTIONS(77), 1,
      anon_sym_LBRACK,
    STATE(40), 1,
      sym__section_header,
    STATE(16), 2,
      sym_section,
      aux_sym_profile_repeat2,
  [244] = 4,
    ACTIONS(30), 1,
      anon_sym_LBRACK,
    ACTIONS(80), 1,
      ts_builtin_sym_end,
    STATE(40), 1,
      sym__section_header,
    STATE(16), 2,
      sym_section,
      aux_sym_profile_repeat2,
  [258] = 2,
    ACTIONS(82), 2,
      ts_builtin_sym_end,
      aux_sym__option_value_multi_line_token1,
    ACTIONS(84), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
  [268] = 2,
    ACTIONS(86), 2,
      ts_builtin_sym_end,
      aux_sym__option_value_multi_line_token1,
    ACTIONS(88), 3,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
  [278] = 4,
    ACTIONS(26), 1,
      anon_sym_DOLLAR_LBRACE,
    ACTIONS(73), 1,
      sym_option_text,
    ACTIONS(90), 1,
      aux_sym__option_value_mono_line_token1,
    STATE(13), 2,
      aux_sym__option_text,
      sym_option_with_reference,
  [292] = 3,
    ACTIONS(94), 1,
      sym_comment,
    STATE(21), 1,
      aux_sym_profile_repeat1,
    ACTIONS(92), 2,
      ts_builtin_sym_end,
      anon_sym_LBRACK,
  [303] = 2,
    ACTIONS(16), 1,
      aux_sym__option_value_multi_line_token1,
    STATE(3), 3,
      sym__option_value_multi_line,
      aux_sym_option_value_repeat1,
      aux_sym__option_value_multi_line_repeat1,
  [312] = 1,
    ACTIONS(97), 4,
      ts_builtin_sym_end,
      anon_sym_LBRACK,
      sym_option_name,
      sym_comment,
  [319] = 3,
    ACTIONS(26), 1,
      anon_sym_DOLLAR_LBRACE,
    ACTIONS(99), 1,
      sym_option_text,
    STATE(15), 2,
      aux_sym__option_text,
      sym_option_with_reference,
  [330] = 1,
    ACTIONS(101), 3,
      aux_sym__option_value_mono_line_token1,
      sym_option_text,
      anon_sym_DOLLAR_LBRACE,
  [336] = 1,
    ACTIONS(103), 3,
      aux_sym__option_value_mono_line_token1,
      sym_option_text,
      anon_sym_DOLLAR_LBRACE,
  [342] = 2,
    ACTIONS(105), 1,
      aux_sym__section_header_token1,
    ACTIONS(107), 1,
      anon_sym_RBRACK,
  [349] = 2,
    ACTIONS(109), 1,
      anon_sym_COLON,
    ACTIONS(111), 1,
      sym_referenced_section,
  [356] = 1,
    ACTIONS(113), 1,
      aux_sym_section_token1,
  [360] = 1,
    ACTIONS(115), 1,
      anon_sym_COLON,
  [364] = 1,
    ACTIONS(117), 1,
      sym_referenced_option,
  [368] = 1,
    ACTIONS(119), 1,
      ts_builtin_sym_end,
  [372] = 1,
    ACTIONS(121), 1,
      aux_sym_option_token1,
  [376] = 1,
    ACTIONS(123), 1,
      anon_sym_RBRACK,
  [380] = 1,
    ACTIONS(125), 1,
      anon_sym_EQ,
  [384] = 1,
    ACTIONS(127), 1,
      aux_sym_section_token1,
  [388] = 1,
    ACTIONS(129), 1,
      anon_sym_RBRACE,
  [392] = 1,
    ACTIONS(131), 1,
      sym_referenced_option,
  [396] = 1,
    ACTIONS(133), 1,
      sym_section_condition,
  [400] = 1,
    ACTIONS(135), 1,
      aux_sym_section_token1,
  [404] = 1,
    ACTIONS(137), 1,
      anon_sym_RBRACE,
  [408] = 1,
    ACTIONS(139), 1,
      sym_section_name,
};

static const uint32_t ts_small_parse_table_map[] = {
  [SMALL_STATE(2)] = 0,
  [SMALL_STATE(3)] = 17,
  [SMALL_STATE(4)] = 34,
  [SMALL_STATE(5)] = 51,
  [SMALL_STATE(6)] = 68,
  [SMALL_STATE(7)] = 88,
  [SMALL_STATE(8)] = 108,
  [SMALL_STATE(9)] = 128,
  [SMALL_STATE(10)] = 143,
  [SMALL_STATE(11)] = 158,
  [SMALL_STATE(12)] = 173,
  [SMALL_STATE(13)] = 188,
  [SMALL_STATE(14)] = 202,
  [SMALL_STATE(15)] = 216,
  [SMALL_STATE(16)] = 230,
  [SMALL_STATE(17)] = 244,
  [SMALL_STATE(18)] = 258,
  [SMALL_STATE(19)] = 268,
  [SMALL_STATE(20)] = 278,
  [SMALL_STATE(21)] = 292,
  [SMALL_STATE(22)] = 303,
  [SMALL_STATE(23)] = 312,
  [SMALL_STATE(24)] = 319,
  [SMALL_STATE(25)] = 330,
  [SMALL_STATE(26)] = 336,
  [SMALL_STATE(27)] = 342,
  [SMALL_STATE(28)] = 349,
  [SMALL_STATE(29)] = 356,
  [SMALL_STATE(30)] = 360,
  [SMALL_STATE(31)] = 364,
  [SMALL_STATE(32)] = 368,
  [SMALL_STATE(33)] = 372,
  [SMALL_STATE(34)] = 376,
  [SMALL_STATE(35)] = 380,
  [SMALL_STATE(36)] = 384,
  [SMALL_STATE(37)] = 388,
  [SMALL_STATE(38)] = 392,
  [SMALL_STATE(39)] = 396,
  [SMALL_STATE(40)] = 400,
  [SMALL_STATE(41)] = 404,
  [SMALL_STATE(42)] = 408,
};

static const TSParseActionEntry ts_parse_actions[] = {
  [0] = {.entry = {.count = 0, .reusable = false}},
  [1] = {.entry = {.count = 1, .reusable = false}}, RECOVER(),
  [3] = {.entry = {.count = 1, .reusable = true}}, SHIFT(7),
  [5] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym_option_value_repeat1, 2),
  [7] = {.entry = {.count = 1, .reusable = false}}, REDUCE(aux_sym_option_value_repeat1, 2),
  [9] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_option_value_repeat1, 2), SHIFT_REPEAT(24),
  [12] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_option_value, 2),
  [14] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_option_value, 2),
  [16] = {.entry = {.count = 1, .reusable = true}}, SHIFT(24),
  [18] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_option_value, 1),
  [20] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_option_value, 1),
  [22] = {.entry = {.count = 1, .reusable = false}}, SHIFT(22),
  [24] = {.entry = {.count = 1, .reusable = false}}, SHIFT(20),
  [26] = {.entry = {.count = 1, .reusable = false}}, SHIFT(28),
  [28] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_profile, 1),
  [30] = {.entry = {.count = 1, .reusable = true}}, SHIFT(42),
  [32] = {.entry = {.count = 1, .reusable = true}}, SHIFT(8),
  [34] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_profile, 2),
  [36] = {.entry = {.count = 1, .reusable = true}}, SHIFT(21),
  [38] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym__option_value_multi_line_repeat1, 2),
  [40] = {.entry = {.count = 1, .reusable = false}}, REDUCE(aux_sym__option_value_multi_line_repeat1, 2),
  [42] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym__option_value_multi_line_repeat1, 2), SHIFT_REPEAT(24),
  [45] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym_section_repeat1, 2),
  [47] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_section_repeat1, 2), SHIFT_REPEAT(35),
  [50] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_section_repeat1, 2), SHIFT_REPEAT(10),
  [53] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_section, 2, .production_id = 1),
  [55] = {.entry = {.count = 1, .reusable = true}}, SHIFT(35),
  [57] = {.entry = {.count = 1, .reusable = true}}, SHIFT(12),
  [59] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_section, 3, .production_id = 1),
  [61] = {.entry = {.count = 1, .reusable = true}}, SHIFT(10),
  [63] = {.entry = {.count = 1, .reusable = false}}, REDUCE(aux_sym__option_text, 2),
  [65] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym__option_text, 2), SHIFT_REPEAT(13),
  [68] = {.entry = {.count = 2, .reusable = false}}, REDUCE(aux_sym__option_text, 2), SHIFT_REPEAT(28),
  [71] = {.entry = {.count = 1, .reusable = false}}, SHIFT(19),
  [73] = {.entry = {.count = 1, .reusable = false}}, SHIFT(13),
  [75] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym_profile_repeat2, 2),
  [77] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_profile_repeat2, 2), SHIFT_REPEAT(42),
  [80] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_profile, 3),
  [82] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym__option_value_mono_line, 2),
  [84] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym__option_value_mono_line, 2),
  [86] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym__option_value_multi_line_repeat1, 3),
  [88] = {.entry = {.count = 1, .reusable = false}}, REDUCE(aux_sym__option_value_multi_line_repeat1, 3),
  [90] = {.entry = {.count = 1, .reusable = false}}, SHIFT(18),
  [92] = {.entry = {.count = 1, .reusable = true}}, REDUCE(aux_sym_profile_repeat1, 2),
  [94] = {.entry = {.count = 2, .reusable = true}}, REDUCE(aux_sym_profile_repeat1, 2), SHIFT_REPEAT(21),
  [97] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym_option, 4),
  [99] = {.entry = {.count = 1, .reusable = true}}, SHIFT(15),
  [101] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_option_with_reference, 4, .production_id = 4),
  [103] = {.entry = {.count = 1, .reusable = false}}, REDUCE(sym_option_with_reference, 5, .production_id = 5),
  [105] = {.entry = {.count = 1, .reusable = true}}, SHIFT(39),
  [107] = {.entry = {.count = 1, .reusable = true}}, SHIFT(36),
  [109] = {.entry = {.count = 1, .reusable = false}}, SHIFT(31),
  [111] = {.entry = {.count = 1, .reusable = true}}, SHIFT(30),
  [113] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym__section_header, 5, .production_id = 3),
  [115] = {.entry = {.count = 1, .reusable = true}}, SHIFT(38),
  [117] = {.entry = {.count = 1, .reusable = true}}, SHIFT(37),
  [119] = {.entry = {.count = 1, .reusable = true}},  ACCEPT_INPUT(),
  [121] = {.entry = {.count = 1, .reusable = true}}, SHIFT(6),
  [123] = {.entry = {.count = 1, .reusable = true}}, SHIFT(29),
  [125] = {.entry = {.count = 1, .reusable = true}}, SHIFT(33),
  [127] = {.entry = {.count = 1, .reusable = true}}, REDUCE(sym__section_header, 3, .production_id = 2),
  [129] = {.entry = {.count = 1, .reusable = true}}, SHIFT(25),
  [131] = {.entry = {.count = 1, .reusable = true}}, SHIFT(41),
  [133] = {.entry = {.count = 1, .reusable = true}}, SHIFT(34),
  [135] = {.entry = {.count = 1, .reusable = true}}, SHIFT(11),
  [137] = {.entry = {.count = 1, .reusable = true}}, SHIFT(26),
  [139] = {.entry = {.count = 1, .reusable = true}}, SHIFT(27),
};

#ifdef __cplusplus
extern "C" {
#endif
#ifdef _WIN32
#define extern __declspec(dllexport)
#endif

extern const TSLanguage *tree_sitter_zcbuildout(void) {
  static const TSLanguage language = {
    .version = LANGUAGE_VERSION,
    .symbol_count = SYMBOL_COUNT,
    .alias_count = ALIAS_COUNT,
    .token_count = TOKEN_COUNT,
    .external_token_count = EXTERNAL_TOKEN_COUNT,
    .state_count = STATE_COUNT,
    .large_state_count = LARGE_STATE_COUNT,
    .production_id_count = PRODUCTION_ID_COUNT,
    .field_count = FIELD_COUNT,
    .max_alias_sequence_length = MAX_ALIAS_SEQUENCE_LENGTH,
    .parse_table = &ts_parse_table[0][0],
    .small_parse_table = ts_small_parse_table,
    .small_parse_table_map = ts_small_parse_table_map,
    .parse_actions = ts_parse_actions,
    .symbol_names = ts_symbol_names,
    .field_names = ts_field_names,
    .field_map_slices = ts_field_map_slices,
    .field_map_entries = ts_field_map_entries,
    .symbol_metadata = ts_symbol_metadata,
    .public_symbol_map = ts_symbol_map,
    .alias_map = ts_non_terminal_alias_map,
    .alias_sequences = &ts_alias_sequences[0][0],
    .lex_modes = ts_lex_modes,
    .lex_fn = ts_lex,
  };
  return &language;
}
#ifdef __cplusplus
}
#endif
