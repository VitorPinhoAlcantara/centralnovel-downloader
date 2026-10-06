import argparse
import json
import math
import os
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--nome", default="shadow_slave")
    p.add_argument("--epocas", type=int, default=6)
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--acumulo", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-6)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--max-amostras", type=int, default=0)
    args = p.parse_args()

    import torch
    from trainer import Trainer, TrainerArgs
    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.tts.datasets import load_tts_samples
    from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTArgs, GPTTrainer, GPTTrainerConfig
    from TTS.tts.models.xtts import XttsAudioConfig

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    base = args.base
    config_dataset = BaseDatasetConfig(
        formatter="coqui",
        dataset_name=args.nome,
        path=args.dataset,
        meta_file_train="metadata.csv",
        language="pt",
    )

    model_args = GPTArgs(
        max_conditioning_length=132300,
        min_conditioning_length=66150,
        debug_loading_failures=False,
        max_wav_length=255995,
        max_text_length=200,
        mel_norm_file=os.path.join(base, "mel_stats.pth"),
        dvae_checkpoint=os.path.join(base, "dvae.pth"),
        xtts_checkpoint=os.path.join(base, "model.pth"),
        tokenizer_file=os.path.join(base, "vocab.json"),
        gpt_num_audio_tokens=1026,
        gpt_start_audio_token=1024,
        gpt_stop_audio_token=1025,
        gpt_use_masking_gt_prompt_approach=True,
        gpt_use_perceiver_resampler=True,
    )
    audio_config = XttsAudioConfig(sample_rate=22050, dvae_sample_rate=22050, output_sample_rate=24000)

    train_samples, eval_samples = load_tts_samples(
        [config_dataset], eval_split=True, eval_split_max_size=64, eval_split_size=0.03
    )
    if args.max_amostras:
        train_samples = train_samples[: args.max_amostras]
    lotes_por_epoca = max(1, math.ceil(len(train_samples) / args.batch))
    print(f"treino: {len(train_samples)} amostras, avaliacao: {len(eval_samples)}, lotes/epoca: {lotes_por_epoca}", flush=True)

    config = GPTTrainerConfig(
        epochs=args.epocas,
        output_path=args.saida,
        model_args=model_args,
        run_name=args.nome,
        project_name="xtts_ft",
        run_description="fine-tune do narrador",
        dashboard_logger="tensorboard",
        logger_uri=None,
        audio=audio_config,
        batch_size=args.batch,
        batch_group_size=48,
        eval_batch_size=args.batch,
        num_loader_workers=args.workers,
        eval_split_max_size=64,
        print_step=50,
        plot_step=100,
        log_model_step=100000,
        save_step=lotes_por_epoca,
        save_n_checkpoints=args.epocas + 1,
        save_checkpoints=True,
        optimizer="AdamW",
        optimizer_wd_only_on_weights=True,
        optimizer_params={"betas": [0.9, 0.96], "eps": 1e-8, "weight_decay": 1e-2},
        lr=args.lr,
        lr_scheduler="MultiStepLR",
        lr_scheduler_params={"milestones": [900000, 2700000, 5400000], "gamma": 0.5, "last_epoch": -1},
        test_sentences=[],
    )

    model = GPTTrainer.init_from_config(config)
    trainer = Trainer(
        TrainerArgs(
            restore_path=None,
            skip_train_epoch=False,
            start_with_eval=False,
            grad_accum_steps=args.acumulo,
        ),
        config,
        output_path=args.saida,
        model=model,
        train_samples=train_samples,
        eval_samples=eval_samples,
    )
    trainer.fit()
    print("TREINO_CONCLUIDO", trainer.output_path, flush=True)


if __name__ == "__main__":
    main()
