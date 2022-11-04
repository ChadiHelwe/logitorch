import pytorch_lightning as pl
import torch.nn as nn
from pytorch_lightning.callbacks import ModelCheckpoint
from torch.utils.data.dataloader import DataLoader

from logitorch.data_collators.ruletaker_collator import RuleTakerCollator
from logitorch.datasets.qa.ruletaker_dataset import RuleTakerDataset
from logitorch.pipelines.exceptions import ModelNotCompatibleError
from logitorch.pl_models.ruletaker import PLRuleTaker


def ruletaker_pipeline(
    model: nn.Module,
    dataset_name: str,
    saved_model_path: str,
    saved_model_name: str,
    batch_size: int,
    epochs: int,
    accelerator: str,
    n_gpus: int,
):
    try:
        if isinstance(model, PLRuleTaker):
            train_dataset = RuleTakerDataset(dataset_name, "train")
            val_dataset = RuleTakerDataset(dataset_name, "val")

            ruletaker_collate_fn = RuleTakerCollator()

            train_dataloader = DataLoader(
                train_dataset, batch_size=batch_size, collate_fn=ruletaker_collate_fn
            )
            val_dataloader = DataLoader(
                val_dataset, batch_size=batch_size, collate_fn=ruletaker_collate_fn
            )

            checkpoint_callback = ModelCheckpoint(
                save_top_k=1,
                monitor="val_loss",
                mode="min",
                dirpath=saved_model_path,
                filename=saved_model_name,
            )

            trainer = pl.Trainer(
                callbacks=[checkpoint_callback],
                accelerator=accelerator,
                gpus=n_gpus,
                max_epochs=epochs,
            )
            trainer.fit(model, train_dataloader, val_dataloader)
        else:
            raise ModelNotCompatibleError()

    except ModelNotCompatibleError as err:
        print(err.message)
