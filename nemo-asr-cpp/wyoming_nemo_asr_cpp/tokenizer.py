"""Hotword phrase -> token-id encoding against the GGUF's own vocab.

The hotword C API (vendored patch, ABI v5) takes token-id sequences, so the
bridge must tokenize phrase text. The SentencePiece pieces are embedded in the
GGUF itself (`parakeet.tokenizer.pieces`, same index order as the model's
logits), so we read them from the already-downloaded model file and do a
greedy longest-match — no extra download, no sentencepiece dependency.

Greedy longest-match can segment differently from the real SentencePiece
unigram model (which uses learned piece scores the GGUF doesn't carry): e.g.
unigram picks '▁'+'일' where greedy picks '▁일', and a sequence that never
matches the decoder's emission stream biases nothing. So each phrase is
encoded as up to two variants — boundary-marker greedy and marker-less
(syllable-fine) greedy — and both are registered; whichever matches the
model's actual segmentation does the work, the other is inert. Verified to
cover real EN + KO emissions.
"""
from __future__ import annotations

import logging
from typing import List, Optional

_LOGGER = logging.getLogger(__name__)

# SentencePiece word-boundary marker (U+2581).
_SPM_SPACE = "▁"


class HotwordTokenizer:
    def __init__(self, gguf_path: str) -> None:
        from gguf import GGUFReader

        field = GGUFReader(gguf_path).fields.get("parakeet.tokenizer.pieces")
        if field is None:
            raise RuntimeError(f"no parakeet.tokenizer.pieces in {gguf_path}")
        self.piece_to_id = {}
        self.max_piece_len = 1
        for tid, part_idx in enumerate(field.data):
            piece = bytes(field.parts[part_idx]).decode("utf-8", "replace")
            # Skip meta tokens (<unk>, language tags) — never valid text matches.
            if piece.startswith("<"):
                continue
            self.piece_to_id.setdefault(piece, tid)
            self.max_piece_len = max(self.max_piece_len, len(piece))

    def _greedy(self, norm: str) -> Optional[List[int]]:
        """Greedy longest-match encode; None if any position has no piece."""
        ids: List[int] = []
        pos = 0
        while pos < len(norm):
            for ln in range(min(self.max_piece_len, len(norm) - pos), 0, -1):
                tid = self.piece_to_id.get(norm[pos : pos + ln])
                if tid is not None:
                    ids.append(tid)
                    pos += ln
                    break
            else:
                # No piece at all here; word-initial form may not exist — retry
                # the same text without the boundary marker.
                if norm[pos] == _SPM_SPACE:
                    pos += 1
                    continue
                return None
        # Drop a *leading* bare "▁" token: it starts most phrases (any word the
        # vocab doesn't merge with ▁), and boosting that ubiquitous token as a
        # phrase start on every decode step destabilizes the argmax at higher
        # boost values. Matching simply starts at the next (distinctive) token.
        space_id = self.piece_to_id.get(_SPM_SPACE)
        while ids and ids[0] == space_id:
            ids.pop(0)
        return ids or None

    def encode_variants(self, phrase: str) -> List[List[int]]:
        """Both segmentation variants of `phrase`, deduplicated (0–2 entries)."""
        text = phrase.strip().replace(" ", _SPM_SPACE)
        variants = []
        for norm in (_SPM_SPACE + text, text):
            ids = self._greedy(norm)
            if ids and ids not in variants:
                variants.append(ids)
        return variants
