import time
from collections.abc import Generator

import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context

from smart_contracts.auction.contract import AuctionContract


@pytest.fixture()
def context() -> Generator[AlgopyTestContext, None, None]:
    with algopy_testing_context() as ctx:
        yield ctx
        ctx.reset()


def test_opt_into_asset(context: AlgopyTestContext) -> None:
    # Arrange
    asset = context.any_asset()  # asset
    contract = AuctionContract()  # init control
    contract.opt_into_asset(asset)

    assert contract.asa.id == asset.id


def test_start_auction(context: AlgopyTestContext) -> None:
    current_timestamp = context.any_uint64(1, 1000)
    duration_timestamp = context.any_uint64(100, 1000)
    # current + duration = end-time
    starting_price = context.any_uint64()
    axfer_txn = context.any_asset_transfer_transaction(
        asset_amount=starting_price, asset_receiver=context.default_application.address
    )
    contract = AuctionContract()
    contract.asa_amount = starting_price
    context.patch_global_fields(latest_timestamp=current_timestamp)
    context.patch_txn_fields(sender=context.default_creator)
    contract.start_auction(
        starting_price=starting_price, length=duration_timestamp, axfer=axfer_txn
    )
    assert contract.auction_end == current_timestamp + duration_timestamp
    assert contract.previous_bid == starting_price
    assert contract.asa_amount == starting_price


def test_bid(context: AlgopyTestContext) -> None:
    account = context.default_creator
    auction_end = context.any_uint64(min_value=int(time.time() + 10_000))
    previous_bid = context.any_uint64(1, 100)
    pay_amount = context.any_uint64(100, 1000)

    contract = AuctionContract()
    contract.auction_end = auction_end
    contract.previous_bid = previous_bid
    pay = context.any_payment_transaction(sender=account, amount=pay_amount)

    contract.bid(pay=pay)

    assert contract.previous_bid == pay_amount
    assert contract.previous_bidder == account
    assert contract.claimable_amount[account] == pay_amount


def test_claim_bids(context: AlgopyTestContext) -> None:
    account = context.any_account()
    context.patch_txn_fields(sender=account)

    contract = AuctionContract()
    claimable_amount = context.any_uint64()
    # address to amount
    contract.claimable_amount[account] = claimable_amount
    contract.previous_bidder = account
    previous_bid = context.any_uint64(max_value=int(claimable_amount))
    contract.previous_bid = previous_bid

    # series to function
    contract.claim_bids()

    amount = claimable_amount - previous_bid
    last_txn = context.last_submitted_itxn.payment

    assert last_txn.amount == amount
    assert last_txn.receiver == account
    assert contract.claimable_amount[account] == claimable_amount - amount
