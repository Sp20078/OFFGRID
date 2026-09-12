from typing import Dict, List
from .file_transfer import FileChunk, FileChunker, FileAssembler
from .delivery import DeliveryManager
from .message import Message


class FileTransferManager:
    def __init__(
        self,
        delivery_manager: DeliveryManager,
        chunk_size: int = 1024
    ):
        self.delivery = delivery_manager
        self.chunker = FileChunker(chunk_size)
        self.assembler = FileAssembler()

        self.files: Dict[str, Dict] = {}

    def create_transfer(
        self,
        source: str,
        destination: str,
        data: bytes,
        ttl: int = 8
    ) -> List[Message]:
        chunks = self.chunker.split(data)

        file_id = chunks[0].file_id

        self.files[file_id] = {
            "source": source,
            "destination": destination,
            "total_chunks": len(chunks),
            "chunks": chunks
        }

        messages = []

        for chunk in chunks:
            message = self.delivery.create_message(
                source=source,
                destination=destination,
                payload=self._encode_chunk(chunk),
                ttl=ttl,
                sequence=chunk.chunk_number
            )

            messages.append(message)

        return messages

    def receive_chunk(self, message: Message) -> str:
        chunk = self._decode_chunk(message.payload)

        if chunk is None:
            return "INVALID_CHUNK"

        result = self.delivery.receive(message)

        if result == "DUPLICATE":
            return "DUPLICATE"

        if result == "EXPIRED":
            return "EXPIRED"

        self.assembler.add_chunk(chunk)

        return "ACCEPTED"

    def is_complete(self, file_id: str) -> bool:
        return self.assembler.is_complete(file_id)

    def assemble_file(self, file_id: str) -> bytes:
        return self.assembler.assemble(file_id)

    def received_chunks(self, file_id: str) -> int:
        return self.assembler.received_chunks(file_id)

    def total_chunks(self, file_id: str) -> int:
        return self.assembler.total_chunks(file_id)

    def get_file_info(self, file_id: str):
        return self.files.get(file_id)

    def remove_file(self, file_id: str):
        self.assembler.remove(file_id)
        self.files.pop(file_id, None)

    @staticmethod
    def _encode_chunk(chunk: FileChunk) -> str:
        return (
            f"{chunk.file_id}|"
            f"{chunk.chunk_number}|"
            f"{chunk.total_chunks}|"
            f"{chunk.data.hex()}"
        )

    @staticmethod
    def _decode_chunk(payload: str):
        try:
            parts = payload.split("|", 3)

            if len(parts) != 4:
                return None

            file_id = parts[0]
            chunk_number = int(parts[1])
            total_chunks = int(parts[2])
            data = bytes.fromhex(parts[3])

            return FileChunk(
                file_id=file_id,
                chunk_number=chunk_number,
                total_chunks=total_chunks,
                data=data
            )

        except (ValueError, TypeError):
            return None
