Coding API - Typed Functions
=============================

Import and call tools like normal Python functions:

.. code-block:: python

    from tooluniverse.tools import UniProt_get_entry_by_accession
    
    # Call the function
    result = UniProt_get_entry_by_accession(accession="P05067")
    print(result)

With Options
------------

.. code-block:: python

    result = UniProt_get_entry_by_accession(
        accession="P05067",
        use_cache=True,
        validate=True
    )

Error Handling
--------------

.. code-block:: python

    from tooluniverse.tools import UniProt_get_entry_by_accession
    from tooluniverse.exceptions import ToolValidationError
    
    try:
        result = UniProt_get_entry_by_accession(accession="invalid")
    except ToolValidationError as e:
        print("Error:", e.message)
        print("What to do:", e.next_steps)

Caching
-------

.. code-block:: python

    from tooluniverse.tools import UniProt_get_entry_by_accession

    # Cache results (enabled by default)
    result = UniProt_get_entry_by_accession(
        accession="P05067",
        use_cache=True  # explicit flag keeps code self-documenting
    )

    # Cache results
    result = UniProt_get_entry_by_accession(
        accession="P05067",
        use_cache=True
    )

Examples
--------

See ``examples/coding_api_example.py`` for more examples.
