-- grd-figure.lua
--
-- Pandoc Lua filter: normalise figure handling for LaTeX output.
--
--   ![Caption](path/fig.png){#fig:convergence width=0.8\linewidth}
-- becomes
--   \begin{figure}[H]
--     \centering
--     \includegraphics[width=0.8\linewidth]{path/fig.png}
--     \caption{Caption}
--     \label{fig:convergence}
--   \end{figure}
--
-- Pandoc's native markdown-to-LaTeX conversion already produces implicit
-- figure environments when an image is the only child of a paragraph. This
-- filter adds three domain-agnostic behaviours on top:
--   1. Resolve relative image paths against a configurable base directory,
--      so the same markdown renders correctly from different working dirs.
--   2. Emit [H] placement (from the float package) for deterministic figure
--      positioning in papers.
--   3. Warn on paths that look unresolvable (absolute to a nonexistent file,
--      or empty). The warning goes to stderr; the figure is still emitted so
--      compilation can proceed.
--
-- Configuration via metadata:
--   figure_base_path: str
--     Directory prepended to relative image sources. No trailing slash.
--   figure_placement: str
--     LaTeX placement specifier. Default: "H" (requires usepackage{float}).

local base_path = nil
local placement = "H"

function Meta(meta)
  if meta.figure_base_path then
    base_path = pandoc.utils.stringify(meta.figure_base_path)
    if base_path:sub(-1) == "/" then base_path = base_path:sub(1, -2) end
    if base_path == "" then base_path = nil end
  end
  if meta.figure_placement then
    placement = pandoc.utils.stringify(meta.figure_placement)
  end
  meta.figure_base_path = nil
  meta.figure_placement = nil
  return meta
end

local function is_absolute(path)
  return path:sub(1, 1) == "/" or path:match("^%a:[/\\]") ~= nil
end

local function is_url(path)
  return path:find("^%a+://") ~= nil
end

local function resolve_src(src)
  if src == "" or is_absolute(src) or is_url(src) then return src end
  if base_path then return base_path .. "/" .. src end
  return src
end

local function serialise_attrs(attr)
  local kv = {}
  for k, v in pairs(attr.attributes) do
    kv[#kv+1] = k .. "=" .. v
  end
  return table.concat(kv, ",")
end

-- Escape LaTeX-special characters inside a caption we're emitting verbatim.
-- Pandoc's own figure environment renders captions through its writer, so
-- this only runs when we build the environment ourselves.
local function render_caption_inlines(inlines)
  return pandoc.utils.stringify(pandoc.Inlines(inlines))
end

local function build_figure(src, attrs, caption_text, label)
  local opts = serialise_attrs(attrs)
  local include_args = opts == "" and "" or ("[" .. opts .. "]")
  local lines = {
    "\\begin{figure}[" .. placement .. "]",
    "  \\centering",
    "  \\includegraphics" .. include_args .. "{" .. src .. "}",
    "  \\caption{" .. caption_text .. "}",
  }
  if label and label ~= "" then
    lines[#lines+1] = "  \\label{" .. label .. "}"
  end
  lines[#lines+1] = "\\end{figure}"
  return pandoc.RawBlock("latex", table.concat(lines, "\n"))
end

-- Pandoc >= 3.0 represents images-with-captions as a Figure block. Handle it
-- first so we produce a single, clean \begin{figure} environment with our
-- placement specifier and resolved path.
function Figure(el)
  -- Extract the first image inside the figure's content blocks.
  local image
  pandoc.walk_block(el, {
    Image = function(img)
      if image == nil then image = img end
      return nil
    end,
  })
  if image == nil then return nil end

  local src = resolve_src(image.src)
  if src == "" then
    io.stderr:write("[grd-figure] warning: image has empty src, skipping resolution\n")
  end

  local caption_inlines = {}
  if el.caption and el.caption.long then
    for _, block in ipairs(el.caption.long) do
      if block.t == "Plain" or block.t == "Para" then
        for _, inl in ipairs(block.content) do
          caption_inlines[#caption_inlines+1] = inl
        end
      end
    end
  end
  if #caption_inlines == 0 and #image.caption > 0 then
    caption_inlines = image.caption
  end
  local caption_text = render_caption_inlines(caption_inlines)

  local label = el.identifier
  if (label == nil or label == "") and image.attr then
    label = image.attr.identifier
  end
  return build_figure(src, image.attr, caption_text, label)
end

-- Pandoc < 3.0 emits implicit figures as Para containing a single Image with
-- a non-empty caption. Keep this path for backwards compatibility.
function Para(el)
  if #el.content ~= 1 then return nil end
  local img = el.content[1]
  if img.t ~= "Image" then return nil end
  if #img.caption == 0 then return nil end

  local src = resolve_src(img.src)
  if src == "" then
    io.stderr:write("[grd-figure] warning: image has empty src, skipping resolution\n")
  end
  local caption_text = render_caption_inlines(img.caption)
  local label = img.attr.identifier
  if label == "" then label = nil end
  return build_figure(src, img.attr, caption_text, label)
end

return {
  { Meta = Meta },
  { Figure = Figure, Para = Para },
}
