import difflib , Levenshtein
from fuzzywuzzy import fuzz, process, string_processing, utils
import numpy as np
import re
import pandas as pd
from itertools import permutations, product, repeat

class CommonReplacements:
    def __init__(self, list_of_pairs):
        self.dict_ = {}
        for one, two in list_of_pairs:
            self.append(one, two)

    def append(self, one, two):

        if one not in self.dict_:
            self.dict_[one] = [two]
        else:
            if two in self.dict_[one]:
                return
            else:
                self.dict_[one].append(two)

        if two not in self.dict_:
            self.dict_[two] = [one]
        else:
            if one in self.dict_[two]:
                return
            else:
                self.dict_[two].append(one)
        return

    def find(self, one, two):
        one = one.lower()
        two = two.lower()
        if one in self.dict_:
            if two in self.dict_[one]:
                return True
        return False


class SimilarityScorer(object):
    def __init__(self, common_replacements, force_ascii=True, verbalize=False):
        self.repl_dict = common_replacements
        self.verbalize = verbalize
        self.force_ascii = force_ascii

    def _buildPrescription(self, D, s, t):
        prescription = [] # собственно, предписание
        i, j = len(s), len(t)
        while i and j:
            insert = D[i][j - 1]
            delete = D[i - 1][j]
            match_or_replace = D[i - 1][j - 1]
            best_choice = min(insert, delete, match_or_replace)
    #         print best_choice, i, j
            if best_choice == match_or_replace:
                if s[i - 1] == t[j - 1]:  # match
                    prescription.append('M')
                else: # replace
                    prescription.append('R')
                i -= 1
                j -= 1
            elif best_choice == insert:
                prescription.append('I')
                j -= 1
            elif best_choice == delete:
                prescription.append('D')
                i -= 1
        while D[i][j] != 0:
            if j - 1 >= 0:
                insert = D[i][j - 1]
            else:
                insert = np.inf
            if i - 1 >= 0:
                delete = D[i - 1][j]
            else:
                delete = np.inf
            if i - 1 >= 0 and j - 1 >= 0:
                match_or_replace = D[i - 1][j - 1]
            else:
                match_or_replace = np.inf
            best_choice = min(insert, delete, match_or_replace)
            if best_choice == match_or_replace:
                if s[i - 1] == t[j - 1]:  # match
                    prescription.append('M')
                else: # replace
                    prescription.append('R')
                i -= 1
                j -= 1
            elif best_choice == insert:
                prescription.append('I')
                j -= 1
            elif best_choice == delete:
                prescription.append('D')
                i -= 1
        prescription.reverse()
        return prescription

    def _countPenaltyForReplacement(self, replacements):
        penalty = 0
        for one, two in replacements:
            if self.repl_dict.find(one, two):
                penalty -= 0.5
            else:
                penalty += 0.5
        return penalty

    def _countPenalty(self, prescription, choice, query):
        penalty = 0 # штраф за удаление / вставку без рядомстоящей замены, слишком маленькую длину choice
        if len(query) - len(choice) == 2:
            penalty += 1
        tmp = ['D'] + prescription + ['D']
        begin = 0
        end = len(tmp) - 1
        while tmp[begin] == "D":
            begin += 1
        while tmp[end] == "D":
            end -= 1
        for p in range(begin, end + 1):
            if tmp[p] == "I" or tmp[p] == "D":
                if tmp[p - 1] != 'R' and tmp[p + 1] != 'R':
                    penalty += 1
        return penalty

    def replacement_search(self, prescription, choice, query):
        choice_pointer = 0
        query_pointer = 0
        replacements = []
        i = 0
        while i < len(prescription):
    #         print prescription[i]
            if prescription[i] == 'M':
                choice_pointer += 1
                query_pointer += 1
                i += 1
            elif prescription[i] == 'R':
                c_left = choice_pointer
                c_right = choice_pointer + 1
                q_left = query_pointer
                q_right = query_pointer + 1
                p_left = i - 1
                p_right = i + 1
    #             print 'choice - ', choice[c_left:c_right], 'query - ', query[q_left:q_right]
                while p_left >= 0:
                    if prescription[p_left] == 'I':
                        q_left -= 1
                        p_left -= 1
                    elif prescription[p_left] == 'D':
                        c_left -= 1
                        p_left -= 1
                    elif prescription[p_left] == 'R':
                        c_left -= 1
                        q_left -= 1
                        p_left -= 1
                    else:
                        break
                while p_right < len(prescription):
                    if prescription[p_right] == 'I':
                        q_right += 1
                        p_right += 1
                    elif prescription[p_right] == 'D':
                        c_right += 1
                        p_right += 1
                    elif prescription[p_right] == 'R':
                        c_right += 1
                        q_right += 1
                        p_right += 1
                    else:
                        break
                replacements.append([choice[c_left:c_right], query[q_left:q_right]])
                choice_pointer = c_right
                query_pointer = q_right
                i = p_right
            elif prescription[i] == 'I':
                query_pointer += 1
                i += 1
            elif prescription[i] == 'D':
                choice_pointer += 1
                i += 1
        return replacements

    def levenshtein(self, choice, query):
        # s - choice, t - query
        m, n = len(choice), len(query)
        D = [range(n + 1)] + [[x + 1] + [None] * n for x in range(m)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if choice[i - 1] == query[j - 1]:
                    D[i][j] = D[i - 1][j - 1]
                else:
                    before_insert = D[i][j - 1]
                    before_delete = D[i - 1][j]
                    before_change = D[i - 1][j - 1]
                    D[i][j] = min(before_insert, before_delete, before_change) + 1
            # поиск предписания проходом от конца к началу
        prescription = self._buildPrescription(np.array(D), choice, query)
        return D[m][n], prescription

    def countDistanceAndPenalty(self, choice, query):
        dist, prescription = self.levenshtein(choice, query)
        replacements = self.replacement_search(prescription, choice, query)
        penalty = self._countPenalty(prescription, choice=choice, query=query)
        penalty2 = self._countPenaltyForReplacement(replacements)
        if self.verbalize:
            print (prescription)
            print ("distance", dist)
            print ("penalty for insertions, deletions and small length", penalty)
            print ("penalty for replacements", penalty2)
        return dist + penalty + penalty2

    def _mymin(self, sorted1, sorted2):
        # если максимум достигается на отсортированных, штраф +0.5
        argmin_i = 0
        mymin_ = np.inf
        for i in range(len(list(product(sorted1, sorted2)))):
            min_ = 0
            if i > 0:
                min_ += 0.5
            one, two = list(product(sorted1, sorted2))[i]
            min_ += self.countDistanceAndPenalty(one, two)
            if min_ < mymin_:
                mymin_ = min_
        return mymin_

    def _process_and_sort(self, s, token_set=False):
        '''
        Process and sort 's' in two modes:
            - For both modes: split 's' by non-alphanumeric chars into 'list_s'.
            1) if token_set is True, sort tokens and return sring of sorted tokens.
            2) if token_set is False, if 'list_s' contatins more than 1 term, return two strings:
            joined 'list_s' and joined sorted 'list_s'. Otherwise, simply return 's'.
        '''
        if self.force_ascii:
            s = utils.asciidammit(s)
        s = s.lower()
        if token_set:
            s = re.sub('[^0-9a-zA-Z]+', '', s)
            return ''.join(sorted(list(s)))
        s = re.sub('[^0-9a-zA-Z]+', ' ', s)
        list_s = s.split(' ')
        if len(list_s) >  1:
            if ''.join(sorted(list_s)) != ''.join(list_s):
                return [''.join(list_s), ''.join(sorted(list_s))]
            else:
                return [''.join(list_s)]
        else:
            return [list_s[0]]

    def _token_sort(self, query, choice, partial=True, myscorer=False, token_set=False):
        if self.verbalize:
            print("Perform token sort for query {0}, choice {1}-------".format(query, choice))
        sorted1 = self._process_and_sort(choice, token_set=False)
        sorted2 = self._process_and_sort(query, token_set=False)
        if self.verbalize:
            print("------Sorted query {0}, sorted choice {1}".format(sorted2, sorted1))
        if token_set:
            query_sorted = self._process_and_sort(query, token_set=True)
            choice_sorted = self._process_and_sort(choice, token_set=True)
            if query_sorted == choice_sorted:
                if myscorer:
                    _ = self._mymin(sorted1, sorted2)
                    if _ > 2.5 and self.verbalize:
                        print ("token_set", 2.5)
                    return min(2.5, _)
                elif partial:
                    return max(97, max([fuzz.partial_ratio(i,j) for i, j in product(sorted1, sorted2)]))
                else:
                    return max(97, max([fuzz.ratio(i,j) for i, j in product(sorted1, sorted2)]))
        if myscorer:
            return self._mymin(sorted1, sorted2)

        if partial:
            score = max([fuzz.partial_ratio(i,j) for i, j in product(sorted1, sorted2)])
            if self.verbalize:
                print("Partial match score {}".format(score))
            return score
        else:
            score = max([fuzz.ratio(i,j) for i, j in product(sorted1, sorted2)])
            if self.verbalize:
                print("Full match score {}".format(score))
            return score


    def my_token_sort_ratio(self, query, choice, myscorer=False, token_set=False):
        """Return a measure of the sequences' similarity between 0 and 100
        but sorting the token before comparing.
        """
        return self._token_sort(query, choice, partial=False, myscorer=myscorer, token_set=token_set)


class DomainMatcher(object):
    def __init__(self, common_replacements, verbalize=False):
        self.repl_dict = common_replacements
        self.verbalize = verbalize

    def _process(self, s, force_ascii=True):
        if force_ascii:
            s = utils.asciidammit(s)
        s = s.lower()
        s = re.sub('[^0-9a-zA-Z]+', '', s)
        return s

    def searchCandidates(self, choices, query, token_set, candidates_limit):
        my_scorer = SimilarityScorer(self.repl_dict, force_ascii=True, verbalize=self.verbalize)

        if self.verbalize:
            print("Select candidates.-------")
        # select 1000 candidates with standart fuzz scorer
        candidates = process.extract(query, choices, limit=candidates_limit, scorer=my_scorer.my_token_sort_ratio)

        # count my score for each candidate based on common replacements and penalties specific fr domain names
        candidate_names = [x[0] for x in candidates]
        candidate_my_scores = [my_scorer.my_token_sort_ratio(query, x, myscorer=True, token_set=token_set)
                               for x in candidate_names]

        # sort candidates by my score
        candidates = list(zip(candidate_names, candidate_my_scores))
        candidates.sort(key=lambda x: x[1])

        return candidates


    def searchNBest(self, N, all_choices, query,
                    token_set=False, candidates_limit=1000):
        '''
        Search 'N' best matches from 'all_choices' given a 'query'.
        Consider only choices which length > (len(query) - 3) and length < (len(query) * 2).
        '''
        candidates = self.searchCandidates(all_choices, query, token_set, candidates_limit)

        # return top N candidates
        return candidates[:N]

def findMatches(all_choices, query):
    COMMON_REPLACEMENTS = [("v", "u"),
                           ("zh", "g"), ("zh", "ge"), ("zh", "j"), ("zh", "je"),
                           ("k", "c"), ("ks", "x"), ("ks", "z"), ("k", "ch"),
                           ("f", "ph"),
                           ("yo", "e"),
                           ("ye", "jo"), ("ye", "io"), ("ye", "eu"),
                           ("ya", "ie"), ("ya", "e"),
                           ("i", "y"), ("iy", "e"),
                           ("e", "o"), ("e", "i"), ("e", "y"),
                           ("j", "y"), ("j", "i"),
                           ("o", "au"),
                           ("y", "w"),
                           ("v", "f"),
                           ("u", "w"),
                           ("s", "c"),
                           ("h", "x"),
                           ]
    N = 20
    all_choices = [domain.name for domain in all_choices]
    repl_dict = CommonReplacements(COMMON_REPLACEMENTS)
    domain_matcher = DomainMatcher(repl_dict, verbalize=False)
    results = domain_matcher.searchNBest(N, all_choices, query)
    return results
