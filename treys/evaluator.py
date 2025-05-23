import itertools
from typing import Sequence

from .card import Card
from .lookup import LookupTable


class Evaluator:
    """
    Evaluates hand strengths using a variant of Cactus Kev's algorithm:
    http://suffe.cool/poker/evaluator.html

    I make considerable optimizations in terms of speed and memory usage, 
    in fact the lookup table generation can be done in under a second and 
    consequent evaluations are very fast. Won't beat C, but very fast as 
    all calculations are done with bit arithmetic and table lookups. 
    """

    HAND_LENGTH = 2
    BOARD_LENGTH = 5

    def __init__(self) -> None:

        self.table = LookupTable()
        
        self.hand_size_map = {
            5: self._five,
            6: self._six,
            7: self._seven
        }

    def evaluate(self, hand: list[int], board: list[int]) -> int:
        """
        This is the function that the user calls to get a hand rank. 

        No input validation because that's cycles!
        """
        all_cards = hand + board
        return self.hand_size_map[len(all_cards)](all_cards)

    def _five(self, cards: Sequence[int]) -> int:
        """
        Performs an evalution given cards in integer form, mapping them to
        a rank in the range [1, 7462], with lower ranks being more powerful.

        Variant of Cactus Kev's 5 card evaluator, though I saved a lot of memory
        space using a hash table and condensing some of the calculations. 
        """
        # if flush
        if cards[0] & cards[1] & cards[2] & cards[3] & cards[4] & 0xF000:
            handOR = (cards[0] | cards[1] | cards[2] | cards[3] | cards[4]) >> 16
            prime = Card.prime_product_from_rankbits(handOR)
            return self.table.flush_lookup[prime]

        # otherwise
        else:
            prime = Card.prime_product_from_hand(cards)
            return self.table.unsuited_lookup[prime]

    def _six(self, cards: Sequence[int]) -> int:
        """
        Performs five_card_eval() on all (6 choose 5) = 6 subsets
        of 5 cards in the set of 6 to determine the best ranking, 
        and returns this ranking.
        """
        minimum = LookupTable.MAX_HIGH_CARD

        for combo in itertools.combinations(cards, 5):

            score = self._five(combo)
            if score < minimum:
                minimum = score

        return minimum

    def _seven(self, cards: Sequence[int]) -> int:
        """
        Performs five_card_eval() on all (7 choose 5) = 21 subsets
        of 5 cards in the set of 7 to determine the best ranking, 
        and returns this ranking.
        """
        minimum = LookupTable.MAX_HIGH_CARD

        for combo in itertools.combinations(cards, 5):
            
            score = self._five(combo)
            if score < minimum:
                minimum = score

        return minimum

    def get_rank_class(self, hr: int) -> int:
        """
        Returns the class of hand given the hand hand_rank
        returned from evaluate. 
        """
        if hr >= 0 and hr <= LookupTable.MAX_ROYAL_FLUSH:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_ROYAL_FLUSH]
        elif hr <= LookupTable.MAX_STRAIGHT_FLUSH:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_STRAIGHT_FLUSH]
        elif hr <= LookupTable.MAX_FOUR_OF_A_KIND:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_FOUR_OF_A_KIND]
        elif hr <= LookupTable.MAX_FULL_HOUSE:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_FULL_HOUSE]
        elif hr <= LookupTable.MAX_FLUSH:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_FLUSH]
        elif hr <= LookupTable.MAX_STRAIGHT:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_STRAIGHT]
        elif hr <= LookupTable.MAX_THREE_OF_A_KIND:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_THREE_OF_A_KIND]
        elif hr <= LookupTable.MAX_TWO_PAIR:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_TWO_PAIR]
        elif hr <= LookupTable.MAX_PAIR:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_PAIR]
        elif hr <= LookupTable.MAX_HIGH_CARD:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_HIGH_CARD]
        else:
            raise Exception("Inavlid hand rank, cannot return rank class")

    def class_to_string(self, class_int: int) -> str:
        """
        Converts the integer class hand score into a human-readable string.
        """
        return LookupTable.RANK_CLASS_TO_STRING[class_int]

    def get_five_card_rank_percentage(self, hand_rank: int) -> float:
        """
        Scales the hand rank score to the [0.0, 1.0] range.
        """
        return float(hand_rank) / float(LookupTable.MAX_HIGH_CARD)


    # def hand_summary(self, board: list[int], hands: list[list[int]]) -> None:
    def hand_summary(self, board: list[int], hands) -> None:
        """
        Gives a sumamry of the hand with ranks as time proceeds. 

        Requires that the board is in chronological order for the 
        analysis to make sense.
        """

        assert len(board) == self.BOARD_LENGTH, "Invalid board length"
        #for hand in hands:
        #   assert len(hand) == self.HAND_LENGTH, "Invalid hand length"

        line_length = 10
        stages = ["FLOP", "TURN", "RIVER"]

        for i in range(len(stages)):
            line = "=" * line_length
            # print("{} {} {}".format(line,stages[i],line))
            
            best_rank = 7463  # rank one worse than worst hand
            winners = []
            # for player, hand in enumerate(hands):
            for player, hand in hands.items():

                # evaluate current board position
                rank = self.evaluate(hand, board[:(i + 3)])
                rank_class = self.get_rank_class(rank)
                class_string = self.class_to_string(rank_class)
                percentage = 1.0 - self.get_five_card_rank_percentage(rank)  # higher better here
                # print("Player {} hand = {}, percentage rank among all hands = {}".format(player + 1, class_string, percentage))

                # detect winner
                if rank == best_rank:
                    winners.append(player)
                    best_rank = rank
                elif rank < best_rank:
                    winners = [player]
                    best_rank = rank

            """
            # if we're not on the river
            if i != stages.index("RIVER"):
                if len(winners) == 1:
                    print("Player {} hand is currently winning.\n".format(winners[0] + 1))
                else:
                    print("Players {} are tied for the lead.\n".format([x + 1 for x in winners]))
            """
            # otherwise on all other streets
            # else:            
            # hand_result = self.class_to_string(self.get_rank_class(self.evaluate(hands[winners[0]], board)))            
            #print("{} HAND OVER {}".format(line, line))
                        
            #if len(winners) == 1:
                #print("Player {} is the winner with a {}\n".format(winners[0] + 1, hand_result))
                #return "Player {} is the winner with a {}\n".format(winners[0] + 1, hand_result)
                #print("Player {} is the winner with a {}\n".format(winners[0], hand_result))
                #return "Player {} is the winner with a {}\n".format(winners[0], hand_result)                
            #else:
                #print("Players {} tied for the win with a {}\n".format([x + 1 for x in winners],hand_result))
                #return "Players {} tied for the win with a {}\n".format([x + 1 for x in winners],hand_result)
                #print("Players {} tied for the win with a {}\n".format([x for x in winners],hand_result))
                #return "Players {} tied for the win with a {}\n".format([x for x in winners],hand_result)                
            
        return winners



class PLOEvaluator(Evaluator):

    HAND_LENGTH = 4

    def evaluate(self, hand: list[int], board: list[int]) -> int:
        minimum = LookupTable.MAX_HIGH_CARD

        for hand_combo in itertools.combinations(hand, 2):
            for board_combo in itertools.combinations(board, 3):
                score = Evaluator._five(self, list(board_combo) + list(hand_combo))
                if score < minimum:
                    minimum = score

        return minimum
