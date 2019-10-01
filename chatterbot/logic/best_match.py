from chatterbot.logic import LogicAdapter
from chatterbot import filters


class BestMatch(LogicAdapter):
    """
    A logic adapter that returns a response based on known responses to
    the closest matches to the input statement.
    """

    def get(self, input_statement):
        """
        Takes a statement string and a list of statement strings.
        Returns the closest matching statement from the list.
        """
        self.chatbot.logger.info('Beginning search for close text match')

        input_search_text = self.chatbot.storage.tagger.get_bigram_pair_string(
            input_statement.text
        )

        statement_list = self.chatbot.storage.filter(
            search_text_contains=input_search_text,
            persona_not_startswith='bot:',
            page_size=self.search_page_size
        )

        closest_match = input_statement
        closest_match.confidence = 0

        self.chatbot.logger.info('Processing search results')

        # Find the closest matching known statement
        for statement in statement_list:
            confidence = self.compare_statements(input_statement, statement)

            if confidence > closest_match.confidence:
                statement.confidence = confidence
                closest_match = statement
                self.chatbot.logger.info('Similar text found: {} {}'.format(
                    closest_match.text, confidence
                ))

            # Stop searching if a match that is close enough is found
            if closest_match.confidence >= self.maximum_similarity_threshold:
                break

        return closest_match

    def can_process(self, statement):
        """
        Check that the chatbot's storage adapter is available to the logic
        adapter and there is at least one statement in the database.
        """
        return self.chatbot.storage.count()

    def process(self, input_statement):

        # Select the closest match to the input statement
        closest_match = self.get(input_statement)
        self.chatbot.logger.info('Using "{}" as a close match to "{}" with a confidence of {}'.format(
            closest_match.text, input_statement.text, closest_match.confidence
        ))

        recent_repeated_responses = filters.get_recent_repeated_responses(
            self.chatbot,
            input_statement.conversation
        )

        # Get all statements that are in response to the closest match
        response_list = list(self.chatbot.storage.filter(
            search_in_response_to=closest_match.search_text,
            exclude_text=recent_repeated_responses,
            exclude_text_words=self.excluded_words
        ))

        if response_list:
            self.chatbot.logger.info(
                'Selecting response from {} optimal responses.'.format(
                    len(response_list)
                )
            )
            response = self.select_response(
                input_statement,
                response_list,
                self.chatbot.storage
            )

            response.confidence = closest_match.confidence
            self.chatbot.logger.info('Response selected. Using "{}"'.format(response.text))
        else:
            response = self.chatbot.storage.get_random()
            self.chatbot.logger.info(
                'No response to "{}" found. Selecting a random response.'.format(
                    closest_match.text
                )
            )

            # Set confidence to zero because a random response is selected
            response.confidence = 0

        return response
