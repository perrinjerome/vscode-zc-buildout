import persistent  # type: ignore
import persistent.list  # type: ignore
import persistent.mapping  # type: ignore
import ZODB  # type: ignore
import ZODB.FileStorage  # type: ignore

import enum
import logging

logger = logging.getLogger(__name__)


class MessageKind(enum.IntEnum):
  Notification = 1
  Request = 2
  Response = 3


class Message(persistent.Persistent):  # type: ignore
  def __init__(self, id: str, kind: MessageKind, payload: str):
    self.id = id
    self.kind = kind
    self.payload = payload


class ProtocolRecorder:
  def __init__(
      self,
      db_path: str,
      session_id: str,
  ) -> None:
    self.db = ZODB.DB(ZODB.FileStorage.FileStorage(db_path))
    self.session_id = session_id

    with self.db.transaction() as cnx:
      if not hasattr(cnx.root, 'messages'):
        cnx.root.messages = persistent.mapping.PersistentMapping()
      if self.session_id not in cnx.root.messages:
        cnx.root.messages[self.session_id] = persistent.list.PersistentList

  def store_message(self, message: Message) -> None:
    with self.db.transaction() as cnx:
      cnx.root.messages[self.session_id].append(message)
