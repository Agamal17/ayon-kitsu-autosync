# -*- coding: utf-8 -*-
import gazu
import pyblish.api
import ayon_api

from openpype.pipeline import KnownPublishError


class CollectKitsuEntities(pyblish.api.ContextPlugin):
    """Collect Kitsu entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu entities"

    def process(self, context):
        project_name = context.data["projectName"]
        kitsu_project = gazu.project.get_project_by_name(project_name)
        if not kitsu_project:
            raise KnownPublishError(
                "Project '{}' not found in kitsu!".format(project_name)
            )

        context.data["kitsuProject"] = kitsu_project
        self.log.debug("Collect kitsu project: {}".format(kitsu_project))

        kitsu_entities_by_id = {}
        for instance in context:
            asset_doc = instance.data.get("assetEntity")
            if not asset_doc:
                continue

            asset_path_parts = list(asset_doc["data"]["parents"])
            asset_path_parts.append(asset_doc["name"])
            asset_path = "/" + "/".join(asset_path_parts)
            kitsu_id = asset_doc["data"].get("kitsuId")
            if not kitsu_id:
                raise KnownPublishError((
                    "Kitsu id not available in AYON for '{}'"
                ).format(asset_path))

            kitsu_entity = kitsu_entities_by_id.get(kitsu_id)
            if not kitsu_entity:
                kitsu_entity = gazu.entity.get_entity(kitsu_id)
                if not kitsu_entity:
                    raise KnownPublishError((
                        "{} was not found in kitsu!"
                    ).format(asset_path))
                kitsu_entities_by_id[kitsu_id] = kitsu_entity

            instance.data["kitsuEntity"] = kitsu_entity

            # Task entity
            task_name = instance.data.get("task")
            if not task_name:
                continue

            task = ayon_api.get_task_by_name(
                project_name, asset_doc["_id"], task_name
            )
            kitsu_task_id = task["attrib"].get("kitsuId")

            self.log.debug("Collect kitsu: {}".format(kitsu_entity))

            if kitsu_task_id:
                kitsu_task = kitsu_entities_by_id.get(kitsu_task_id)
                if not kitsu_task:
                    kitsu_task = gazu.task.get_task(kitsu_task_id)
            else:
                kitsu_task_type = gazu.task.get_task_type_by_name(task_name)
                if not kitsu_task_type:
                    raise KnownPublishError(
                        "Task type {} not found in Kitsu!".format(task_name)
                    )

                kitsu_task = gazu.task.get_task_by_name(
                    kitsu_entity, kitsu_task_type
                )

            if not kitsu_task:
                raise KnownPublishError(
                    "Task {} not found in kitsu!".format(task_name)
                )

            kitsu_entities_by_id[kitsu_task["id"]] = kitsu_task

            instance.data["kitsuTask"] = kitsu_task
            self.log.debug("Collect kitsu task: {}".format(kitsu_task))
