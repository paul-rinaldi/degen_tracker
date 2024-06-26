
import hypersync
import asyncio
import time
from hypersync import TransactionField, LogField

# Sample stand alone script to fetch erc20 tokens and print relevant decoded values.
# Modified from this example - https://github.com/enviodev/hypersync-client-python/blob/main/examples/all-erc20.py


async def fetch_erc20s():
    client = hypersync.HypersyncClient("https://base.hypersync.xyz")

    # The query to run
    query = hypersync.Query(
        # Full sync
        from_block=0,
        logs=[hypersync.LogSelection(
            # We want All ERC20 transfers so no address filter and only a filter for the first topic
            topics=[
                ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]]
        )],
        # Select the fields we are interested in, notice topics are selected as topic0,1,2,3
        field_selection=hypersync.FieldSelection(
            log=[el.value for el in LogField],
            transaction=[el.value for el in TransactionField],
            block=[el.value for el in hypersync.BlockField]
        )
    )

    print("Running the query...")

    tx_data = []
    log_data = []
    block_data = []
    # Continuously fetch data until the end of the specified period is reached.
    while True:
        # Send the query to the blockchain client.
        res = await client.send_req(query)

        # read json abi file for erc20
        with open('./src/degen_tracker/abis/erc20.json', 'r') as json_file:
            abi = json_file.read()

        # Map of contract_address -> abi
        abis = {}

        # every log we get should be decodable by this abi but we don't know
        # the specific contract addresses since we are indexing all erc20 transfers.
        for log in res.data.logs:
            abis[log.address] = abi

        # Create a decoder with our mapping
        decoder = hypersync.Decoder(abis)

        # Decode the log on a background thread so we don't block the event loop.
        # Can also use decoder.decode_logs_sync if it is more convenient.
        decoded_logs = await decoder.decode_logs(res.data.logs)

        # Append the fetched transactions and log to their respective lists.
        tx_data += res.data.transactions
        log_data += decoded_logs
        block_data += res.data.blocks

        # Check if the fetched data has reached the current archive height or next block.
        if res.archive_height < res.next_block:
            # Exit the loop if the end of the period (or the blockchain's current height) is reached.
            break

        # Update the query to fetch the next set of data starting from the next block.
        query.from_block = res.next_block
        print(f"Scanned up to block {query.from_block}")  # Log progress.

        # print(log_data[0])
        # print(log_data[0].body)
        # print(log_data[0].indexed)

        # print(res.data.transactions[0])
        # print(res.data.blocks[0])
        print("# of logs", len(log_data))
        print('# of blocks', len(block_data))


start_time = time.time()
asyncio.run(fetch_erc20s())
print("--- %s seconds ---" % (time.time() - start_time))
