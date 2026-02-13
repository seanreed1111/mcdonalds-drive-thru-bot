---
description: Convert a markdown blog post to Substack-friendly format (tables/code → images, strip bold)
---

# Convert Markdown to Substack Format

Convert the specified markdown file to a Substack-friendly format by running the conversion script.

The file path is: $ARGUMENTS

## Process:

1. **Validate the input:**
   - Confirm the file exists and is a markdown file
   - If `$ARGUMENTS` is empty, ask the user for the file path

2. **Run the conversion script:**
   ```bash
   uv run python scripts/convert_to_substack.py $ARGUMENTS
   ```

3. **Report results:**
   - Show the output file path
   - Show how many code blocks and tables were converted to images
   - Note any issues encountered

## What the script does:
- Fenced code blocks → syntax-highlighted PNG images (light theme) in `./images/`
- Markdown tables → clean table PNG images in `./images/`
- Bold text (`**text**`, `__text__`) → plain text
- Output written to `<original-name>-substack.md` in the same directory
