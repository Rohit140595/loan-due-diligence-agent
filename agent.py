# TODO (Module 4): build the agent loop here.
#
# Rough shape (fill in as we go through Module 4 together):
#
# 1. Load strategy.md contents -> use as the `system` prompt
# 2. Define the `tools` list (name, description, input_schema) for each
#    function in tools/
# 3. Send initial message (applicant_id) to Claude with system + tools
# 4. Loop:
#       - if Claude's response contains a tool_use block:
#           - execute the corresponding Python function from tools/
#           - send the result back as a tool_result message
#       - if Claude's response is plain text (final summary):
#           - stop the loop, return the result
#
# Keep this loop visible and simple at first -- no framework (LangChain/etc)
# so the mechanics from Module 2 stay obvious.

if __name__ == "__main__":
    pass
