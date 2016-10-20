#!/usr/bin/env python
# coding: utf-8


from asyncio import StreamReader, StreamWriter


class SMTPStreamReader(StreamReader):
    """
    """
    # RFC 2821 § 4.5.3.1 says a line is max. 512 chars long.
    # We chose to support a bit more :o)
    line_max_length = 8192

    def __init__(self, limit=line_max_length, loop=None):
        """
        Initializes a new SMTPStreamReader instance.
        """
        super().__init__(limit, loop)

    async def read_reply(self):
        """
        Reads a reply from the server.

        Raises:
            ConnectionResetError: If the connection with the server is lost
                (we can't read any response anymore). Or if the server
                replies without a proper return code.

        Returns:
            (int, str): A (code, full_message) 2-tuple consisting of:

                - server response code ;
                - server response string corresponding to response code
                  (multiline responses are returned in a single string).
        """
        code = 500
        messages = []
        go_on = True

        while go_on:
            try:
                line = await self.readline()
            except ValueError as e:
                # ValueError is raised when limit is reached before we could
                # get an entire line.
                # We return what we got with a 500 code and we stop to read
                # the reply to avoid being flooded.
                code = 500
                go_on = False
            else:
                try:
                    code = int(line[:3])
                except ValueError as e:
                    # We either:
                    # - Got an empty line (connection is probably down),
                    # - Got a line without a valid return code.
                    # In both case, it shouldn't happen, hence:
                    raise ConnectionResetError('Connection lost.') from e
                else:
                    # Check is we have a multiline response:
                    go_on = (line[3:4] == b'-')

            message = line[4:].strip(b' \t\r\n').decode('ascii')
            messages.append(message)

        full_message = "\n".join(messages)

        return code, full_message


class SMTPStreamWriter(StreamWriter):
    """
    """
    async def send_command(self, *args):
        """
        Sends the given command (and parameters, if any) to the server.

        Raises:
            ConnectionResetError: If the connection with the server is lost.
            (Shouldn't it raise BrokenPipeError too ?)
        """
        command = "{}\r\n".format(" ".join(args)).encode('ascii')

        self.write(command)

        # Don't forget to drain or the command will stay buffered:
        await self.drain()
