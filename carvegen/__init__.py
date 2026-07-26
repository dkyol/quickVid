"""carvegen — generate viral-style continuous carving videos with Kling AI.

A whole watermelon (or wood block) is progressively carved into a detailed
subject across a sequence of stitched segments:

    outline -> peeling -> deep carving -> final details

Each segment is a Kling video generation (image-to-video preferred, with an
optional end keyframe via `image_tail`), stitched by ffmpeg into one 9:16
Reels/TikTok-ready clip.

See CARVEGEN.md for the full guide, recommended settings, and prompt templates.
"""

__version__ = "0.1.0"
