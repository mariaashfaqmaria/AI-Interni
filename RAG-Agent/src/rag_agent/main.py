from .search import search
from .chain import chain


def main():

    # ----------------------------------------
    # Get question from user
    # ----------------------------------------

    question = input("\nAsk a question: ")


    # ----------------------------------------
    # Search Pinecone
    # ----------------------------------------

    results = search(question, k=3)


    # ----------------------------------------
    # Check whether results were found
    # ----------------------------------------

    if not results:
        print("\nAnswer:")
        print("I don't know based on the provided document.")
        return


    # ----------------------------------------
    # Display similarity scores
    # ----------------------------------------

    print("\nRetrieved chunks:")

    for i, (document, score) in enumerate(results, start=1):

        print("\n" + "=" * 60)
        print(f"RESULT {i}")
        print("=" * 60)

        print("Similarity score:", score)
        print(document.page_content)


    # ----------------------------------------
    # Create context from retrieved chunks
    # ----------------------------------------

    context = "\n\n".join(
        document.page_content
        for document, score in results
    )


    # ----------------------------------------
    # Send context + question to LLM
    # ----------------------------------------

    response = chain.invoke({
        "context": context,
        "question": question
    })


    # ----------------------------------------
    # Display final answer
    # ----------------------------------------

    print("\nAnswer:")
    print(response.content)


if __name__ == "__main__":
    main()