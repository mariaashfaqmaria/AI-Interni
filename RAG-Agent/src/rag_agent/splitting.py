import re

from langchain_core.documents import Document

from src.rag_agent.document_loading import load_pdf


# --------------------------------------------------
# 1. Detect whether a line is a main topic heading
# --------------------------------------------------

def is_topic_heading(line):
    pattern = r"^\d+\.\s+.+$"
    return bool(re.match(pattern, line.strip()))


# --------------------------------------------------
# 2. Split documents according to topics
# --------------------------------------------------

def split_by_topic(documents):

    topic_documents = []

    current_topic = None
    current_content = []

    for document in documents:

        # Get text from the loaded document
        text = document.page_content

        # Split page into individual lines
        lines = text.split("\n")

        for line in lines:

            line = line.strip()

            # Ignore empty lines
            if not line:
                continue

            # --------------------------------------
            # New topic detected
            # --------------------------------------

            if is_topic_heading(line):

                # Save previous topic
                if current_topic is not None:

                    topic_text = "\n".join(current_content)

                    topic_documents.append(
                        Document(
                            page_content=topic_text,
                            metadata={
                                "topic": current_topic
                            }
                        )
                    )

                # Start new topic
                current_topic = line
                current_content = [line]

            else:

                # Add content to current topic
                if current_topic is not None:
                    current_content.append(line)

    # ----------------------------------------------
    # Save final topic
    # ----------------------------------------------

    if current_topic is not None:

        topic_text = "\n".join(current_content)

        topic_documents.append(
            Document(
                page_content=topic_text,
                metadata={
                    "topic": current_topic
                }
            )
        )

    return topic_documents


# --------------------------------------------------
# 3. Main function
# --------------------------------------------------

def split_pdf():

    documents = load_pdf()

    print("Number of loaded documents:", len(documents))

    # Topic-based splitting
    chunks = split_by_topic(documents)

    print("Number of topic-based chunks:", len(chunks))

    # Display information about chunks
    for i, chunk in enumerate(chunks):

        print("\n" + "=" * 60)
        print(f"Chunk {i + 1}")
        print("Topic:", chunk.metadata["topic"])
        print("Characters:", len(chunk.page_content))
        print("-" * 60)

        print(chunk.page_content[:300])

    return chunks


# --------------------------------------------------
# 4. Run program
# --------------------------------------------------

if __name__ == "__main__":
    split_pdf()