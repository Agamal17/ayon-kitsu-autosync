import re

from typing import Any
from nxtools import slugify, logging

from ayon_server.lib.postgres import Postgres
from ayon_server.entities import FolderEntity, TaskEntity
from ayon_server.events import dispatch_event


def create_name_and_label(kitsu_name: str) -> dict[str, str]:
    """From a name coming from kitsu, create a name and label"""
    name_slug = slugify(kitsu_name, separator="_")
    return {"name": name_slug, "label": kitsu_name}



async def get_folder_by_kitsu_id(
    project_name: str,
    kitsu_id: str,
    existing_folders: dict[str, str] | None = None,
) -> FolderEntity:
    """Get an Ayon FolderEndtity by its Kitsu ID"""

    if existing_folders and (kitsu_id in existing_folders):
        folder_id = existing_folders[kitsu_id]

    else:
        res = await Postgres.fetch(
            f"""
            SELECT id FROM project_{project_name}.folders
            WHERE data->>'kitsuId' = $1
            """,
            kitsu_id,
        )
        if not res:
            return None
        folder_id = res[0]["id"]

    return await FolderEntity.load(project_name, folder_id)

    return None


async def get_task_by_kitsu_id(
    project_name: str,
    kitsu_id: str,
    existing_tasks: dict[str, str] | None = None,
) -> TaskEntity:
    """Get an Ayon TaskEntity by its Kitsu ID"""

    if existing_tasks and (kitsu_id in existing_tasks):
        folder_id = existing_tasks[kitsu_id]

    else:
        res = await Postgres.fetch(
            f"""
            SELECT id FROM project_{project_name}.tasks
            WHERE data->>'kitsuId' = $1
            """,
            kitsu_id,
        )
        if not res:
            return None
        folder_id = res[0]["id"]

    return await TaskEntity.load(project_name, folder_id)

    return None


async def create_folder(
    project_name: str,
    name: str,
    **kwargs,
) -> FolderEntity:
    """
    TODO: This is a re-implementation of create folder, which does not
    require background tasks. Maybe just use the similar function from
    api.folders.folders.py?
    """
    payload = {**kwargs, **create_name_and_label(name)}

    folder = FolderEntity(
        project_name=project_name,
        payload=payload,
    )
    await folder.save()
    event = {
        "topic": "entity.folder.created",
        "description": f"Folder {folder.name} created",
        "summary": {"entityId": folder.id, "parentId": folder.parent_id},
        "project": project_name,
    }

    await dispatch_event(**event)
    return folder

async def update_folder(
    project_name: str,
    folder_id: str,
    name: str,
    **kwargs,
) -> bool:
    
    folder = await FolderEntity.load(project_name, folder_id)
    changed = False

    payload = {**kwargs, **create_name_and_label(name)}

    for key in ['name', 'label']:
        if key in payload and getattr(folder, key) != payload[key]:
            setattr(folder, key, payload[key])
            changed = True

    for key, value in payload['attrib'].items():
        if getattr(folder.attrib, key) != value:
            setattr(folder.attrib, key, value)
            if key not in folder.own_attrib:
                folder.own_attrib.append(key)
            changed = True
    if changed:
        await folder.save()
        event = {
            "topic": "entity.folder.updated",
            "description": f"Folder {folder.name} updated",
            "summary": {"entityId": folder.id, "parentId": folder.parent_id},
            "project": project_name,
        }
        await dispatch_event(**event)

    return changed


async def create_task(
    project_name: str,
    name: str,
    **kwargs,
) -> TaskEntity:
    payload = {**kwargs, **create_name_and_label(name)}

    task = TaskEntity(
        project_name=project_name,
        payload=payload,
    )
    await task.save()
    event = {
        "topic": "entity.task.created",
        "description": f"Task {task.name} created",
        "summary": {"entityId": task.id, "parentId": task.parent_id},
        "project": project_name,
    }

    await dispatch_event(**event)
    return task

async def update_task(
    project_name: str,
    task_id: str,
    name: str,
    **kwargs,
) -> bool:
    
    task = await TaskEntity.load(project_name, task_id)
    changed = False

    payload = {**kwargs, **create_name_and_label(name)}

    # keys that can be updated
    for key in ['name', 'label', 'status', 'task_type']:
        if key in payload and getattr(task, key) != payload[key]:
            setattr(task, key, payload[key])
            changed = True
    if 'attrib' in payload:
        for key, value in payload['attrib'].items():
            if getattr(task.attrib, key) != value:
                setattr(task.attrib, key, value)
                if key not in task.own_attrib:
                    task.own_attrib.append(key)
                changed = True
    if changed:
        await task.save()
        event = {
            "topic": "entity.task.updated",
            "description": f"Task {task.name} updated",
            "summary": {"entityId": task.id, "parentId": task.parent_id},
            "project": project_name,
        }
        await dispatch_event(**event)
    return changed