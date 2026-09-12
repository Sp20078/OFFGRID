from backend.messaging.file_transfer import FileChunker, FileAssembler


def test_file_is_split_into_chunks():
    data = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    chunker = FileChunker(chunk_size=5)
    chunks = chunker.split(data)

    assert len(chunks) == 6
    assert chunks[0].chunk_number == 0
    assert chunks[0].total_chunks == 6
    assert chunks[0].data == b"ABCDE"
    assert chunks[5].data == b"Z"


def test_file_chunks_can_be_reassembled():
    data = b"OFFGRID emergency communication system"

    chunker = FileChunker(chunk_size=5)
    assembler = FileAssembler()

    chunks = chunker.split(data)

    for chunk in chunks:
        assembler.add_chunk(chunk)

    file_id = chunks[0].file_id

    assert assembler.received_chunks(file_id) == len(chunks)
    assert assembler.total_chunks(file_id) == len(chunks)
    assert assembler.is_complete(file_id) is True

    result = assembler.assemble(file_id)

    assert result == data


def test_out_of_order_chunks_are_reassembled_correctly():
    data = b"ABCDEFGHIJKLMNO"

    chunker = FileChunker(chunk_size=3)
    assembler = FileAssembler()

    chunks = chunker.split(data)

    for chunk in reversed(chunks):
        assembler.add_chunk(chunk)

    file_id = chunks[0].file_id

    assert assembler.is_complete(file_id) is True
    assert assembler.assemble(file_id) == data


def test_incomplete_file_cannot_be_assembled():
    data = b"OFFGRID FILE TRANSFER"

    chunker = FileChunker(chunk_size=4)
    assembler = FileAssembler()

    chunks = chunker.split(data)

    for chunk in chunks[:-1]:
        assembler.add_chunk(chunk)

    file_id = chunks[0].file_id

    assert assembler.is_complete(file_id) is False

    try:
        assembler.assemble(file_id)
        assert False
    except ValueError:
        assert True


def test_duplicate_chunk_does_not_break_file():
    data = b"OFFGRID"

    chunker = FileChunker(chunk_size=3)
    assembler = FileAssembler()

    chunks = chunker.split(data)

    assembler.add_chunk(chunks[0])
    assembler.add_chunk(chunks[0])
    assembler.add_chunk(chunks[1])
    assembler.add_chunk(chunks[2])

    file_id = chunks[0].file_id

    assert assembler.received_chunks(file_id) == 3
    assert assembler.is_complete(file_id) is True
    assert assembler.assemble(file_id) == data


def test_empty_file():
    chunker = FileChunker(chunk_size=5)
    assembler = FileAssembler()

    chunks = chunker.split(b"")

    assert len(chunks) == 1
    assert chunks[0].data == b""

    assembler.add_chunk(chunks[0])

    file_id = chunks[0].file_id

    assert assembler.is_complete(file_id) is True
    assert assembler.assemble(file_id) == b""
