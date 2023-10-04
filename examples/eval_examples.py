from sklearn.metrics import accuracy_score
from tqdm import tqdm
import json
import statistics
from collections import defaultdict

from logitorch.datasets.proof_qa.proofwriter_dataset import (
    PROOFWRITER_LABEL_TO_ID,
    ProofWriterDataset,
)
from logitorch.datasets.proof_qa.fld_dataset import FLDDataset
from logitorch.datasets.qa.ruletaker_dataset import RuleTakerDataset
from logitorch.datasets.te.mnli_dataset import MNLIDataset
from logitorch.datasets.te.negated_mnli_dataset import NegatedMNLIDataset
from logitorch.datasets.te.negated_rte_dataset import NegatedRTEDataset
from logitorch.datasets.te.negated_snli_dataset import NegatedSNLIDataset
from logitorch.datasets.te.rte_dataset import RTEDataset
from logitorch.datasets.te.snli_dataset import SNLIDataset
from logitorch.pl_models.bertnot import PLBERTNOT
from logitorch.pl_models.proofwriter import PLProofWriter
from logitorch.pl_models.prover import PLPRover
from logitorch.pl_models.fld import PLFLDAllAtOnceProver
from logitorch.pl_models.ruletaker import PLRuleTaker
from evaluate import load

# MODEL = "ruletaker"
# DEVICE = "cpu"

MODEL = "FLD"
DEVICE = "cuda"


def parse_facts_rules(facts, rules):
    sentences = []
    for k, v in facts.items():
        sentences.append(f"{k}: {v}")
    for k, v in rules.items():
        sentences.append(f"{k}: {v}")
    context = "".join(sentences)
    return context


proofwriter_test_datasets = ["depth-5", "birds-electricity"]

if MODEL == "proofwriter":
    model = PLProofWriter.load_from_checkpoint(
        "models/best_proofwriter-epoch=05-val_loss=0.01.ckpt",
        pretrained_model="google/t5-v1_1-large",
    )
    model.to(DEVICE)
    model.eval()

    for d in proofwriter_test_datasets:
        test_dataset = ProofWriterDataset(d, "test", "proof_generation_all")
        depths_pred = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        depths_true = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        y_preds = []
        y_trues = []

        for i in tqdm(test_dataset):
            context = parse_facts_rules(i[0], i[1])
            y_pred = model.predict(context, i[2], device=DEVICE)
            if "True" in y_pred:
                y_pred = 1
            else:
                y_pred = 0
            y_true = PROOFWRITER_LABEL_TO_ID[str(i[3])]
            depths_pred[i[6]].append(y_pred)
            depths_true[i[6]].append(y_true)
            y_preds.append(y_pred)
            y_trues.append(y_true)

        for k in depths_pred:
            with open(f"proofwriter_{d}_{k}.txt", "w") as out:
                out.write(str(accuracy_score(depths_pred[k], depths_true[k])))

        with open(f"proofwriter_{d}.txt", "w") as out:
            out.write(str(accuracy_score(y_preds, y_trues)))

elif MODEL == "prover":
    model = PLPRover.load_from_checkpoint(
        "models/best_prover-epoch=09-val_loss=0.07.ckpt",
        pretrained_model="roberta-large",
    )
    model.to(DEVICE)
    model.eval()

    for d in proofwriter_test_datasets:
        test_dataset = ProofWriterDataset(d, "test", "proof_generation_all")
        depths_pred = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        depths_true = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        y_preds = []
        y_trues = []

        for i in tqdm(test_dataset):
            y_pred = model.predict(i[0], i[1], i[2], device=DEVICE)
            y_true = PROOFWRITER_LABEL_TO_ID[str(i[3])]
            depths_pred[i[6]].append(y_pred)
            depths_true[i[6]].append(y_true)
            y_preds.append(y_pred)
            y_trues.append(y_true)

        for k in depths_pred:
            with open(f"prover_{d}_{k}.txt", "w") as out:
                out.write(str(accuracy_score(depths_pred[k], depths_true[k])))

        with open(f"prover_{d}.txt", "w") as out:
            out.write(str(accuracy_score(y_preds, y_trues)))

elif MODEL == "FLD":
    model = PLFLDAllAtOnceProver.load_from_checkpoint(
        "models/best_fld-epoch=12-val_loss=0.06.ckpt",
        pretrained_model="t5-base",
    )
    model.to(DEVICE)
    model.eval()

    test_dataset = FLDDataset("hitachi-nlp/FLD.v2", "test", "proof_generation_all", max_samples=10)

    # fld_metrics = load('/home/acb11878tj/work/projects/FLD-metrics/FLD_metrics.py')
    fld_metrics = load('hitachi-nlp/FLD_metrics')

    metrics = defaultdict(list)
    for i in tqdm(test_dataset):
        pred = model.predict(i['prompt_serial'], device=DEVICE)

        # from FLD_task import log_example
        # log_example(
        #     context=i['context'],
        #     hypothesis=i['hypothesis'],
        #     gold_proofs=[i['proof_serial']],
        #     pred_proof=pred,
        # )

        _metrics = fld_metrics.compute(
            predictions=[pred],
            references=[[i['proof_serial']]],
            contexts=[i['context']],
        )

        depths = (['all', str(i['depth'])] if i.get('depth', None) is not None
                  else ['all', 'None'])
        for depth in depths:
            for metric_name, metric_val in _metrics.items():
                metrics[f"D-{depth}.{metric_name}"].append(metric_val)

    results = {}
    for metric_name, metric_vals in metrics.items():
        results[f"{metric_name}"] = statistics.mean(metric_vals)

    json.dump(results, open("fld_results.json", "w"),
              ensure_ascii=False, indent=4, sort_keys=True, separators=(',', ': '))

elif MODEL == "ruletaker":
    model = PLRuleTaker.load_from_checkpoint(
        "models/best_ruletaker_ruletaker-epoch=05-val_loss=0.03.ckpt"
    )
    model.to(DEVICE)
    model.eval()

    for d in proofwriter_test_datasets:
        test_dataset = RuleTakerDataset(d, "test")
        depths_pred = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        depths_true = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
        y_preds = []
        y_trues = []

        for i in tqdm(test_dataset):
            y_pred = model.predict(i[0], i[1], device=DEVICE)
            y_true = i[2]
            depths_pred[i[3]].append(y_pred)
            depths_true[i[3]].append(y_true)
            y_preds.append(y_pred)
            y_trues.append(y_true)

        for k in depths_pred:
            with open(f"ruletaker_1_{d}_{k}.txt", "w") as out:
                out.write(str(accuracy_score(depths_pred[k], depths_true[k])))

        with open(f"ruletaker_1_{d}.txt", "w") as out:
            out.write(str(accuracy_score(y_preds, y_trues)))

elif MODEL == "bertnot":
    model = PLBERTNOT.load_from_checkpoint(
        "models/snli_bertnot.ckpt", pretrained_model="bert-base-cased", num_labels=3
    )
    model.to(DEVICE)
    val_dataset = SNLIDataset("val")
    neg_dataset = NegatedSNLIDataset()

    with open("bertnot_val_snli.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in val_dataset:

            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))

    with open("bertnot_neg_snli.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in neg_dataset:
            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))

    model = PLBERTNOT.load_from_checkpoint(
        "models/mnli_bertnot.ckpt", pretrained_model="bert-base-cased", num_labels=3
    )
    model.to(DEVICE)
    val_dataset = MNLIDataset("val")
    neg_dataset = NegatedMNLIDataset()

    with open("bertnot_val_mnli.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in val_dataset:

            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))

    with open("bertnot_neg_mnli.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in neg_dataset:
            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))

    model = PLBERTNOT.load_from_checkpoint(
        "models/rte_bertnot.ckpt", pretrained_model="bert-base-cased", num_labels=2
    )
    model.to(DEVICE)
    val_dataset = RTEDataset("val")
    neg_dataset = NegatedRTEDataset()

    with open("bertnot_val_rte.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in val_dataset:

            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))

    with open("bertnot_neg_rte.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in neg_dataset:
            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))
elif MODEL == "rte":
    model = PLBERTNOT.load_from_checkpoint(
        "models/rte_bertnot.ckpt", pretrained_model="bert-base-cased", num_labels=2
    )
    model.to(DEVICE)
    val_dataset = RTEDataset("val")
    neg_dataset = NegatedRTEDataset()

    with open("bertnot_val_rte.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in val_dataset:

            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))

    with open("bertnot_neg_rte.txt", "w") as out:
        y_preds = []
        y_trues = []
        for p, h, l in neg_dataset:
            y_pred = model.predict(p, h, task="te", device=DEVICE)
            y_preds.append(y_pred)
            y_trues.append(l)
        out.write(str(accuracy_score(y_trues, y_preds)))
