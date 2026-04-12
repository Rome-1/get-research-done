-- grd-math.lua
--
-- Pandoc Lua filter: normalise math environments so LLM-authored markdown
-- produces correct LaTeX.
--
-- Behaviour:
--   1. Display math followed by a {#eq:label} attribute (same paragraph) is
--      emitted as a numbered \begin{equation}\label{eq:label}...\end{equation}
--      block. Authors write
--          $$ E = mc^2 $$ {#eq:einstein}
--      and get a referenceable equation without hand-writing the environment.
--   2. Stray LaTeX commands that escaped math mode (e.g. "\alpha" sitting in
--      prose) are wrapped in inline math as an AST-level safety net. This is
--      the same category of bug that grd/utils/latex.py's regex auto-fix
--      targets -- catching it here prevents malformed output.
--
-- Domain-agnostic: no physics-notation assumptions. Works for any field that
-- writes equations in markdown.
--
-- Configuration via metadata:
--   math_autowrap: bool
--     When true (default), apply the heuristic backslash-detection wrap.
--     Turn off if your prose legitimately contains raw LaTeX commands outside
--     math mode.

local autowrap = true

function Meta(meta)
  if meta.math_autowrap ~= nil then
    local v = pandoc.utils.stringify(meta.math_autowrap):lower()
    autowrap = not (v == "false" or v == "no" or v == "0" or v == "off")
  end
  meta.math_autowrap = nil
  return meta
end

local function build_equation(math_text, label)
  local body
  if label and label ~= "" then
    body = "\\begin{equation}\n" .. math_text .. "\n\\label{eq:" .. label .. "}\n\\end{equation}"
  else
    body = "\\begin{equation}\n" .. math_text .. "\n\\end{equation}"
  end
  return pandoc.RawBlock("latex", body)
end

-- Trim leading/trailing whitespace.
local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- When pandoc sees "$$...$$ {#eq:label}" the default representation is a Para
-- containing a DisplayMath followed by a Space and an inline attribute set
-- that pandoc typically attaches to the math. Promote the whole thing to a
-- \begin{equation} when a label is present.
function Para(el)
  if #el.content == 0 then return nil end
  -- Detect: a single Math element (DisplayMath) optionally followed by whitespace
  -- and a `{#eq:xxx}` block written by the author.
  local math_el = nil
  local rest = {}
  for _, node in ipairs(el.content) do
    if node.t == "Math" and node.mathtype == "DisplayMath" and math_el == nil then
      math_el = node
    elseif math_el ~= nil then
      rest[#rest+1] = node
    else
      return nil  -- bail out if something precedes the math
    end
  end
  if math_el == nil then return nil end

  -- Check rest for a `{#eq:label}` pattern (pandoc may fragment this).
  local buf = {}
  for _, r in ipairs(rest) do
    if r.t == "Str" then buf[#buf+1] = r.text
    elseif r.t == "Space" or r.t == "SoftBreak" then buf[#buf+1] = " "
    else return nil  -- unknown residue; don't touch
    end
  end
  local tail = trim(table.concat(buf))
  if tail == "" then
    -- No label -- still convert to \[...\] canonical form? Leave pandoc's default.
    return nil
  end
  local label = tail:match("^{#eq:([%w%-_]+)}$")
  if not label then return nil end
  return build_equation(math_el.text, label)
end

-- AST-level detection of "looks like LaTeX fell out of math mode" -- a
-- frequent LLM failure. Conservative: we only act on Str runs that contain a
-- backslash command like \alpha, \int, \frac, etc.
local LIKELY_COMMAND = "\\%a+"

local function looks_like_stray_latex(s)
  -- Must contain at least one backslash command AND no surrounding spaces
  -- that would imply prose.
  if s:find(LIKELY_COMMAND) == nil then return false end
  -- Exclude common prose words that start with backslash-escaped characters.
  if s:find("^\\[_%^%&%%%$%{%}#]") then return false end
  return true
end

function Str(el)
  if not autowrap then return nil end
  if not looks_like_stray_latex(el.text) then return nil end
  -- Wrap the content in an inline math element so pandoc emits $...$.
  return pandoc.Math("InlineMath", el.text)
end

return {
  { Meta = Meta },
  { Para = Para, Str = Str },
}
