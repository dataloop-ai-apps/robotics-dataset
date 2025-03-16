import json
import logging
import os
import zipfile
from functools import partial

import dtlpy as dl
import requests

logger = logging.getLogger(name='sustAGE')


class sustAGE(dl.BaseServiceRunner):
    def __init__(self):
        self.logger = logger
        self.logger.info('Initializing dataset loader')

    def upload_dataset(self, dataset: dl.Dataset, source: str, progress=None):
        """
        Uploads a text dataset to the specified destination.

        Args:
            dataset (dl.Dataset): The dataset object to upload.
            source (str): The source URL of the dataset.
            progress (optional): An optional progress object to track the upload progress.

        Returns:
            None

        Raises:
            requests.exceptions.RequestException: If there is an issue with the HTTP request.
            zipfile.BadZipFile: If the downloaded zip file is corrupted.
            KeyError: If there is an issue with the dataset metadata or configuration.
        """

        if progress is not None:
            progress.update(
                progress=0,
                message='Creating dataset...',
                status='Creating dataset...'
            )

        self.logger.info('Downloading zip file...')
        direc = os.getcwd()
        zip_dir = os.path.join(direc, "sustAGE Actions+Postures videos.zip")

        if not os.path.exists(zip_dir):
            response = requests.get(source, timeout=100)
            if response.status_code == 200:
                with open(zip_dir, 'wb') as f:
                    f.write(response.content)
            else:
                self.logger.error(
                    'Failed to download the file. Status code: %s', response.status_code
                )
                return

        with zipfile.ZipFile(zip_dir, 'r') as zip_ref:
            zip_ref.extractall(direc)
        self.logger.info('Zip file downloaded and extracted.')

        if progress is not None:
            progress.update(
                progress=0,
                message='Uploading items and annotations ...',
                status='Uploading items and annotations ...',
            )

        progress_tracker = {'last_progress': 0}

        def progress_callback_all(progress_class, progress, context):
            new_progress = progress // 2
            if (
                new_progress > progress_tracker['last_progress']
                and new_progress % 5 == 0
            ):
                logger.info(f'Progress: {new_progress}%')
                progress_tracker['last_progress'] = new_progress
                if progress_class is not None:
                    progress_class.update(
                        progress=new_progress,
                        message='Uploading items and annotations ...',
                        status='Uploading items and annotations ...',
                    )

        progress_callback = partial(progress_callback_all, progress)

        dl.client_api.add_callback(
            func=progress_callback, event=dl.CallbackEvent.ITEMS_UPLOAD
        )

        annotations_files = os.path.join(direc, 'json/')
        items_files = os.path.join(direc, 'items/')
        dataset.items.upload(
            local_path=items_files,
            local_annotations_path=annotations_files,
        )

        # Setup dataset recipe and ontology
        recipe = dataset.recipes.list()[0]
        ontology = recipe.ontologies.list()[0]
        with open(os.path.join(direc, 'sustAGE Actions+Postures videos-ontology.json'), 'r') as f:
            ontology_json = json.load(f)
        ontology.copy_from(ontology_json=ontology_json)

        self.logger.info('Dataset uploaded successfully')
