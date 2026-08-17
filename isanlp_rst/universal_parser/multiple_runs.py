"""
Script for multiple runs of experiments.

For monolingual experiments run:
    # Train
    python universal_parser/multiple_runs.py --corpus "$CORPUS" --lang "$LANG" --model_type "$TYPE" train
    # Evaluation
    python universal_parser/multiple_runs.py --corpus "$CORPUS" --lang "$LANG" --model_type "$TYPE" evaluate

For multilingual experiments:
    # Train
    python universal_parser/multiple_runs.py --corpus 'GUM' --lang "$LANG" --model_type "$TYPE" train_mixed --mixed 100
    # Evaluation (with saves/path-with-models/run_N)
    python utils/eval_dmrst_transfer.py --models_dir saves/path-with-models \
                                        --corpus 'GUM' --lang 'en' --nfolds 5 evaluate
"""

import json
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import fire


class MultipleRunnerGeneral:
    def __init__(
        self,
        corpora: list[str],
        lang: str,
        model_type: str,
        transformer_name: str = 'xlm-roberta-large',
        emb_size: int = 1024,
        freeze_first_n: int = 0,
        window_size: int = 400,
        window_padding: int = 55,
        cuda_device: int = 0,
        resume_training: bool = False,
        n_runs: int = 5,
        save_path: str = 'saves/',
    ) -> None:
        """
        :param corpora: corpus names, e.g. ['GUM'] or ['RST-DT']
        :param lang: 'en' or 'ru'
        :param model_type: one of {'default', '+tony', '+tony+trainable_edus', '+tony+trainable_edus+bimpm'}
        :param transformer_name: model name or path to the pretrained LM
        :param emb_size: LM encodings size
        :param cuda_device: number of cuda device
        :param resume_training: whether to rewrite previous saves
        """
        self.corpora = corpora
        self.lang = lang
        self.model_type = model_type
        self.transformer_name = transformer_name
        self.emb_size = emb_size
        self.freeze_first_n = freeze_first_n
        self.window_size = window_size
        self.window_padding = window_padding
        self.cuda_device = cuda_device
        self.resume_training = resume_training
        self.n_runs = n_runs
        self.save_path = save_path

    def _general_parameters(self) -> dict[str, object]:
        overrides: dict[str, object] = {
            'corpora': self.corpora,
            'lang': self.lang,
            'cross_validation': 'false',
            'second_lang_fold': 0,
            'second_lang_fraction': 0,
            'transformer_name': self.transformer_name,  # LM name
            'emb_size': self.emb_size,  # LM embedding size
            'freeze_first_n': self.freeze_first_n,  # LM fine-tuning configuration
            'window_size': self.window_size,
            'window_padding': self.window_padding,
            'transformer_normalize': 'true',
            'hidden_size': 768,
            'use_crf': 'true',  # ToNy (LSTM-CRF)
            'use_log_crf': 'false',  # [Optional] Logits restriction for ToNy
            'token_bilstm_hidden': 300,  # BiMPM representation hidden size
            'batch_size': 2,
            'dwa_bs': 12,  # Batch size for DWA computation
            'grad_clipping_value': 10.0,
            'combine_batches': 'false',  # [Optional] Combine batches w/smallest trees (for normalization when bs=1)
            'lr': 0.0001,
            'cuda_device': self.cuda_device,
            'save_path': self.save_path,
        }

        # Default parameters
        overrides.update({
            'segmenter_type': 'linear',
            'segmenter_hidden_dim': overrides['hidden_size'],
            'segmenter_dropout': 0.4,
            'lstm_bidirectional': 'true',
            'if_edu_start_loss': 'true',
            'edu_encoding_kind': 'avg',
            'rel_classification_kind': 'default',
            'use_discriminator': 'false',
            'discriminator_warmup': 0,
        })

        if self.model_type != 'default':
            types = self.model_type.split('+')

            if 'tony' in types:
                overrides['segmenter_type'] = 'tony'
                overrides['if_edu_start_loss'] = 'false'
                overrides['segmenter_hidden_dim'] = 200

                if 'RuRSTB' in self.corpora:
                    overrides['segmenter_dropout'] = 0.5

            if 'no_crf' in types:
                overrides['use_crf'] = 'false'

            if 'trainable_edus' in types:
                overrides['edu_encoding_kind'] = 'trainable'

            if 'gru_edus' in types:
                overrides['edu_encoding_kind'] = 'gru'

            if 'bigru_edus' in types:
                overrides['edu_encoding_kind'] = 'bigru'

            if 'bilstm_edus' in types:
                overrides['edu_encoding_kind'] = 'bilstm'

            if 'trainable_dus' in types:
                overrides['du_encoding_kind'] = 'trainable'

            if 'bimpm' in types:
                overrides['rel_classification_kind'] = 'with_bimpm'

            if 'al' in types:
                overrides['use_discriminator'] = 'true'
                overrides['discriminator_warmup'] = 3

        return overrides

    def _get_variants(self) -> Iterable[int]:
        return range(40, 40 + self.n_runs)  # There is a fixed split, we just change the nn random seed

    def train(self) -> None:
        general_parameters = self._general_parameters()
        for run in self._get_variants():
            general_parameters['foldnum'] = 0
            general_parameters['seed'] = run

            general_parameters['run_name'] = f'{self.lang}_{"+".join(self.corpora)}_{self.model_type}_{run}'
            for key, value in general_parameters.items():
                general_parameters[key] = str(value)

            if self.resume_training:
                metrics_path = Path('saves') / str(general_parameters['run_name']) / 'best_metrics.json'
                if metrics_path.is_file():
                    continue

            p = subprocess.Popen(
                ['python', 'universal_parser/trainer.py',
                 'configs/general_uni_config.jsonnet', json.dumps(general_parameters)],
                stdout=sys.stdout, stderr=sys.stderr
            )
            p.wait()

    def evaluate(self) -> None:
        results: dict[str, list[object]] = {
            'e2e_test_f1_full': [],
            'e2e_test_f1_nuc': [],
            'e2e_test_f1_rel': [],
            'e2e_test_f1_seg': [],
            'e2e_test_f1_span': [],
            'gs_test_f1_full': [],
            'gs_test_f1_nuc': [],
            'gs_test_f1_rel': [],
            'gs_test_f1_span': []
        }
        for run in self._get_variants():
            run_name = f'{self.lang}_{"+".join(self.corpora)}_{self.model_type}_{run}'
            run_path = Path(self.save_path) / run_name
            try:
                all_metrics = list(run_path.glob('metrics_epoch_*.json'))
                best_epoch = sorted(int(metrics.name[14:-5]) for metrics in all_metrics)[-1]
                best_dev_metrics = json.loads(
                    (run_path / f'metrics_epoch_{best_epoch}.json').read_text(encoding='utf-8')
                )
                for key in results:
                    results[key].append(best_dev_metrics[key])
            except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError):
                print(f'Run {run} is missing.')

        with Path(f'{self.lang}_{"+".join(self.corpora)}_{self.model_type}_all_res.json').open('w') as f:
            json.dump(results, f)

    def train_mixed(self, mixed: int) -> None:
        """ Running training with second language injection of ``mixed`` % """

        save_path = Path('saves_mixed')
        save_path.mkdir(exist_ok=True)

        general_parameters = self._general_parameters()
        general_parameters['save_path'] = str(save_path)

        for run in range(self.n_runs):
            assert 'GUM' in self.corpora  # Cross-lingual training is only for parallel corpus

            general_parameters['foldnum'] = 0
            general_parameters['seed'] = 40
            general_parameters.update({
                'second_lang_fold': run,
                'second_lang_fraction': mixed,
            })

            general_parameters['run_name'] = f'{self.lang}_{mixed}perc_{run}'
            for key, value in general_parameters.items():
                general_parameters[key] = str(value)

            if self.resume_training:
                metrics_path = save_path / str(general_parameters['run_name']) / 'best_metrics.json'
                if metrics_path.is_file():
                    continue

            p = subprocess.Popen(
                ['python', 'universal_parser/trainer.py',
                 'configs/general_uni_config.jsonnet', json.dumps(general_parameters)],
                stdout=sys.stdout, stderr=sys.stderr
            )
            p.wait()


if __name__ == '__main__':
    fire.Fire(MultipleRunnerGeneral)
