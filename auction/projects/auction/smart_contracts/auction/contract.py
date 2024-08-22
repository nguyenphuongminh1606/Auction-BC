from algopy import (
    Account,
    ARC4Contract,
    Asset,
    Global,
    LocalState,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
)


class AuctionContract(ARC4Contract):
    def __init__(self) -> None:
        self.auction_end = UInt64(0)
        self.previous_bid = UInt64(0)
        self.asa_amount = UInt64(0)
        self.asa = Asset()  # ASA Algorand standard assets
        self.previous_bidder = Account()
        self.claimable_amount = LocalState(
            UInt64, key="claim", description="the claimable amount"
        )

    # Opt asset #VBI Tokens
    @arc4.abimethod
    def opt_into_asset(self, asset: Asset) -> None:
        assert Txn.sender == Global.creator_address, "only creator has access"
        assert self.asa.id == 0, "ASA already opt in"
        self.asa = asset
        itxn.AssetTransfer(
            xfer_asset=asset, asset_receiver=Global.current_application_address
        ).submit()

    # Start auction
    @arc4.abimethod
    def start_auction(
        self,
        length: UInt64,
        starting_price: UInt64,
        axfer: gtxn.AssetTransferTransaction,
    ) -> None:
        assert Txn.sender == Global.creator_address, "you're owner of auction"
        assert (
            axfer.asset_receiver == Global.current_application_address
        ), "axfer must be transferred to this app"
        assert self.auction_end == 0, "Auction ended"

        self.asa_amount = axfer.asset_amount
        self.auction_end = length + Global.latest_timestamp
        self.previous_bid = starting_price

    @arc4.abimethod
    def opt_in(self) -> None:
        pass

    # Bids
    @arc4.abimethod
    def bid(self, pay: gtxn.PaymentTransaction) -> None:
        # Kiem tra buoi dau gia ket thuc chua
        assert Global.latest_timestamp < self.auction_end, "auction ended"

        # verify payments
        assert pay.sender == Txn.sender  # payment sender must match transa sender
        assert pay.amount > self.previous_bid
        # set data on global state
        self.previous_bid = pay.amount
        self.previous_bidder = pay.sender

        # update claimable amount
        self.claimable_amount[Txn.sender] = pay.amount

    # Claim Bids
    @arc4.abimethod
    def claim_bids(self) -> None:
        amount = original_amount = self.claimable_amount[Txn.sender]

        if Txn.sender == self.previous_bidder:
            amount -= self.previous_bid

        itxn.Payment(
            amount=amount,
            receiver=Txn.sender,
        ).submit()

        self.claimable_amount[Txn.sender] = original_amount - amount

    @arc4.abimethod
    def claim_asset(
        self, asset: Asset
    ) -> None:  # Truyen sp dau gia cho nguoi thang cuoc
        assert (
            Txn.sender == Global.creator_address
        ), "auction must be started by creator"
        assert Global.latest_timestamp > self.auction_end, "auction not end yet"

        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=self.previous_bidder,
            asset_close_to=self.previous_bidder,
            asset_amount=self.asa_amount,
        ).submit()

    # Delete Application
    @arc4.abimethod(allow_actions=["DeleteApplication"])
    def delete_appplication(self) -> None:
        itxn.Payment(
            close_remainder_to=Global.creator_address, receiver=Global.creator_address
        ).submit()

    ####
    def clear_state_program(self) -> bool:
        return True
