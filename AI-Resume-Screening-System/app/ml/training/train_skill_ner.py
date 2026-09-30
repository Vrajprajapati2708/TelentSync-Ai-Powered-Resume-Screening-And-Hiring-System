# ============================================================
#  TalentSync — spaCy SKILL NER Trainer (Python 3.14 compatible)
#
#  On Python 3.14+, spaCy cannot be installed due to
#  Cython/blis compilation issues.
#  This module gracefully skips NER training and logs a notice.
#
#  The skill extraction pipeline automatically falls back to the
#  regex + sklearn hybrid, which is still highly effective.
# ============================================================

import sys
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SPACY_NOT_AVAILABLE_MSG = (
    "spaCy NER training is not available on Python 3.14+ "
    "due to upstream Cython/blis compatibility issues. "
    "Skill extraction will use the regex + sklearn TF-IDF hybrid, "
    "which provides very good accuracy. "
    "To enable NER, use Python 3.11 or 3.12."
)


def train_ner_model(n_iter: int = 30, dropout: float = 0.3,
                    batch_size_start: float = 4.0,
                    batch_size_end: float = 32.0) -> str:
    """
    Attempt to train the spaCy NER model.

    Falls back gracefully on Python 3.14+ where spaCy cannot be
    compiled due to the blis/Cython compatibility limitation.

    Returns:
        Path to model dir if trained, or 'SKIPPED' if not available.
    """
    # ── Try to import spaCy first ─────────────────────────────
    try:
        import spacy
    except ImportError:
        logger.warning(_SPACY_NOT_AVAILABLE_MSG)
        print(f"\n  [NOTICE] {_SPACY_NOT_AVAILABLE_MSG}\n")
        return "SKIPPED"

    # ── If spaCy is available, run real training ──────────────
    import json
    import time
    import random
    from pathlib import Path
    from spacy.training import Example
    from spacy.util import minibatch
    from thinc.schedules import compounding
    from spacy.pipeline.ner import EntityRecognizer
    from typing import cast

    from app.ml.training.generate_dataset import generate_dataset

    BASE_DIR     = Path(__file__).resolve().parents[4]
    DATASET_DIR  = BASE_DIR / "datasets"
    MODEL_DIR    = BASE_DIR / "trained_models" / "spacy_skill_ner"

    logger.info("=" * 60)
    logger.info("TalentSync — spaCy SKILL NER Training")
    logger.info("=" * 60)

    # Load or generate dataset
    ner_data_path = DATASET_DIR / "ner_training_data.json"
    if ner_data_path.exists():
        with open(ner_data_path, "r", encoding="utf-8") as f:
            ner_training_data = json.load(f)
    else:
        dataset = generate_dataset(
            num_resumes=600, num_jobs=0, output_dir=str(DATASET_DIR)
        )
        ner_training_data = dataset["ner_training_data"]

    nlp = spacy.blank("en")
    if "ner" not in nlp.pipe_names:
        ner_pipe = nlp.add_pipe("ner", last=True)
    else:
        ner_pipe = nlp.get_pipe("ner")
    ner = cast(EntityRecognizer, ner_pipe)
    ner.add_label("SKILL")

    # Prepare examples
    examples = []
    for item in ner_training_data:
        text     = item["text"]
        entities = item.get("entities", [])
        doc      = nlp.make_doc(text)
        ents     = []
        for start, end, label in entities:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span:
                ents.append(span)
        ents = spacy.util.filter_spans(ents)
        gold = {"entities": [(e.start_char, e.end_char, e.label_) for e in ents]}
        try:
            examples.append(Example.from_dict(doc, gold))
        except Exception:
            pass

    random.shuffle(examples)
    split    = int(len(examples) * 0.9)
    train_ex = examples[:split]
    dev_ex   = examples[split:]

    optimizer   = nlp.begin_training()
    batch_sizes = compounding(batch_size_start, batch_size_end, 1.001)
    best_score  = 0.0
    history     = []

    for epoch in range(n_iter):
        random.shuffle(train_ex)
        losses = {}
        for batch in minibatch(train_ex, size=batch_sizes):
            nlp.update(batch, drop=dropout, losses=losses, sgd=optimizer)

        tp, fp, fn = 0, 0, 0
        for ex in dev_ex:
            pred_doc  = nlp(ex.reference.text)
            pred_ents = {(e.start_char, e.end_char) for e in pred_doc.ents}
            gold_ents = {(e.start_char, e.end_char) for e in ex.reference.ents}
            tp += len(pred_ents & gold_ents)
            fp += len(pred_ents - gold_ents)
            fn += len(gold_ents - pred_ents)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)

        history.append({
            "epoch": epoch + 1, "loss": round(losses.get("ner", 0), 4),
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)
        })

        log_msg = (f"Epoch {epoch+1:02d}/{n_iter} | "
                   f"Loss: {losses.get('ner', 0):.4f} | "
                   f"P: {precision:.3f} | R: {recall:.3f} | F1: {f1:.3f}")

        if f1 >= best_score:
            best_score = f1
            log_msg += "  <- best"
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            nlp.to_disk(str(MODEL_DIR))

        logger.info(log_msg)

    def _make_serializable(obj):
        import numpy as np
        if isinstance(obj, dict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_make_serializable(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(_make_serializable(v) for v in obj)
        elif isinstance(obj, (np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    history_path = MODEL_DIR / "training_history.json"
    with open(history_path, "w") as f:
        metadata = {
            "model": "spacy_skill_ner",
            "epochs": n_iter,
            "best_f1": round(best_score, 4),
            "history": history
        }
        json.dump(_make_serializable(metadata), f, indent=2)

    return str(MODEL_DIR)


if __name__ == "__main__":
    train_ner_model(n_iter=30, dropout=0.3)
