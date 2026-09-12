from dataclasses import dataclass
from typing import Dict, List
from uuid import uuid4


@dataclass
class FileChunk:
    file_id: str
    chunk_number: int
    total_chunks: int
    data: bytes

    def to_dict(self):
        return {
            "file_id": self.file_id,
            "chunk_number": self.chunk_number,
            "total_chunks": self.total_chunks,
            "data": self.data
        }


class FileChunker:
    def __init__(self, chunk_size: int = 1024):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        self.chunk_size = chunk_size

    def split(self, data: bytes, file_id: str = None) -> List[FileChunk]:
        if file_id is None:
            file_id = str(uuid4())

        if not data:
            return [
                FileChunk(
                    file_id=file_id,
                    chunk_number=0,
                    total_chunks=1,
                    data=b""
                )
            ]

        total_chunks = (
            len(data) + self.chunk_size - 1
        ) // self.chunk_size

        chunks = []

        for start in range(0, len(data), self.chunk_size):
            chunk_number = start // self.chunk_size

            chunks.append(
                FileChunk(
                    file_id=file_id,
                    chunk_number=chunk_number,
                    total_chunks=total_chunks,
                    data=data[start:start + self.chunk_size]
                )
            )

        return chunks


class FileAssembler:
    def __init__(self):
        self.files: Dict[str, Dict[int, bytes]] = {}
        self.metadata: Dict[str, int] = {}

    def add_chunk(self, chunk: FileChunk):
        if chunk.file_id not in self.files:
            self.files[chunk.file_id] = {}
            self.metadata[chunk.file_id] = chunk.total_chunks

        self.files[chunk.file_id][chunk.chunk_number] = chunk.data

    def received_chunks(self, file_id: str) -> int:
        return len(self.files.get(file_id, {}))

    def total_chunks(self, file_id: str) -> int:
        return self.metadata.get(file_id, 0)

    def is_complete(self, file_id: str) -> bool:
        if file_id not in self.files:
            return False

        total = self.metadata[file_id]
        chunks = self.files[file_id]

        if len(chunks) != total:
            return False

        return all(
            number in chunks
            for number in range(total)
        )

    def assemble(self, file_id: str) -> bytes:
        if not self.is_complete(file_id):
            raise ValueError("File is incomplete")

        chunks = self.files[file_id]

        return b"".join(
            chunks[number]
            for number in range(self.metadata[file_id])
        )

    def remove(self, file_id: str):
        self.files.pop(file_id, None)
        self.metadata.pop(file_id, None)