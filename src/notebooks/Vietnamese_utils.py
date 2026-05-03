import unicodedata
import re
import json

class VietnameseSyllable:
    def __init__(self, initial: str, glide: str, nucleus: str, final: str, tone: str):
        self.initial = initial
        self.glide = glide
        self.nucleus = nucleus
        self.final = final
        self.tone = tone

    def __str__(self):
        syllable = ""
        if self.initial:
            syllable += self.initial
        if self.glide:
            syllable += self.glide
        if self.nucleus:
            syllable += self.nucleus
        if self.final:
            syllable += self.final
        if self.tone:
            syllable += self.tone

        return syllable

    def compose_Vietnamese_word(self, Vietnamese_word_path: str) -> str:
    
        Vietnamese_words = json.load(open(Vietnamese_word_path))
        Vietnamese_words = set([word for words in Vietnamese_words for word in words])

        onsets = VietnamesePhonemesToGraphemes.Initial[self.initial]
        medials = VietnamesePhonemesToGraphemes.Glide[self.glide]
        vowels = VietnamesePhonemesToGraphemes.Nucleus[self.nucleus]
        codas = VietnamesePhonemesToGraphemes.Final[self.final]
        tone = VietnamesePhonemesToGraphemes.Tone[self.tone]

        # # check for the semivowels
        # if any([coda in ["o", "u", "i", "y"] for coda in codas]):
        #     if any([vowel in ["a", "ə"] for vowel in vowels]):
        #         if "u" in codas:
        #             codas.remove("u")
        #         if "y" in codas:
        #             codas.remove("y")
        #     elif any([vowel in ["ă", "ə̆"] for vowel in vowels]):
        #         if "o" in codas:
        #             codas.remove("o")
        #         if "i" in codas:
        #             codas.remove("i")

        possible_words = []
        for onset in onsets:
            for medial in medials:
                for vowel in vowels:
                    for coda in codas:
                        if is_Vietnamese(onset, medial, vowel, coda, tone):
                            # process for the special case of medial + coda (hỏa, thủy, thuở, thỏa, ...)
                            # in this case, only "thuở" follows the general rule of tone marking, the others are the case that tones are marked on the medial.
                            if (onset != "q") and (medial != "") and (vowel != "") and (coda == "") and (vowel != "ơ"):
                                medial += tone
                            else:
                                if coda == "":
                                    _vowel = vowel[0] + tone + vowel[1:]
                                else:
                                    _vowel = vowel + tone

                            word = ""

                            word += onset
                            word += medial
                            word += _vowel
                            word += coda

                            if "gii" in word:
                                word = re.sub("gii", "gi", word)

                            word = unicodedata.normalize("NFC", word)
                            
                            if word in Vietnamese_words:
                                possible_words.append(word)

        return possible_words
    
    def __repr__(self): # Add this for JSON serialization
        return self.__str__()

class VietnameseGraphemesToPhonemes:
    Initial: dict[str, str] = {
        "ngh": "ŋ",
        "ng": "ŋ",
        "ph": "f",
        "th": "tʰ",
        "dz": "ʝ",
        "gi": "ʝ",
        "gh": "ɣ",
        "gk": "ɣ",
        "ch": "t͡ɕ",
        "ck": "t͡ɕ",
        "tr": "ʈ͡ʂ",
        "nh": "ɲ",
        "nk": "ɲ",
        "kh": "χ",
        "qu": "kʷ",
        "f": "f",
        "m": "m",
        "b": "b",
        "p": "b",
        "c": "k",
        "k": "k",
        "v": "ʝ", 
        "d": "ʝ", 
        "j": "ʝ",
        "z": "ʝ",
        "y": "ʝ",
        "t": "t",
        "đ": "d",
        "n": "n",
        "r": "r",
        "x": "s", 
        "s": "s",
        "l": "l",
        "h": "h",
        "g": "ɣ",
        "w": "kʷ"
    }
    
    Glide: dict[str, str] = {
        "u": "u̯",
        "o": "u̯"
    }

    Nucleus: dict[str, str] = {
        "iê": "iə",
        "yê": "iə",
        "ia": "iə",
        "ya": "iə",
        "uô": "uə",
        "ua": "uə",
        "ươ": "ɯə",
        "ưa": "ɯə",
        "uh": "u",
        "a": "a",
        "ă": "ă",
        "â": "ə̆",
        "i": "i",
        "j": "i",
        "y": "i",
        "e": "ɛ",
        "ê": "e",
        "u": "u",
        "ư": "ɯ",
        "o": "ɔ",
        "oo": "ɔ",
        "ô": "o",
        "ơ": "ə"
    }

    Final: dict[str, str] = {
        "nh": "ŋ̟",
        "nk": "ŋ̟",
        "ng": "ŋ",
        "ngk": "ŋ",
        "ch": "k̟",
        "i": "j",
        "y": "j",
        "m": "m",
        "n": "n",
        "p": "p",
        "t": "t",
        "c": "k",
        "k": "k",
        "u": "u̯",
        "o": "u̯"
    }

class VietnameseDecomposer:
    @classmethod
    def get_tone(self, word: str) -> tuple[str, str]:
        tone_map = {
            '\u0300': '˨˩',
            '\u0301': '˧˥',
            '\u0303': '˧ˀ˥',
            '\u0309': '˧˩',
            '\u0323': '˧ˀ˩',
        }
        decomposed_word = unicodedata.normalize('NFD', word)
        tone = None
        remaining_word = ''
        for char in decomposed_word:
            if char in tone_map:
                tone = tone_map[char]
            else:
                remaining_word += char
        remaining_word = unicodedata.normalize('NFC', remaining_word)
        
        return tone, remaining_word

    @classmethod
    def get_onset(self, word: str) -> tuple[str, str]:
        onsets = list(VietnameseGraphemesToPhonemes.Initial.keys())
    
        # get the onset
        for onset in onsets:
            if word.startswith(onset):
                if onset != "q": # leaving "qu" for the later get_medial function
                    word = word.removeprefix(onset)
                return onset, word

        return None, word

    @classmethod
    def get_medial(self, word: str) -> tuple[str, str]:
        O_MEDIAL = "o"
        U_MEDIAL = "u"

        if word.startswith("q"):
            # in Vietnamese, words starting with "q" always has "u" as the medial
            word = word.removeprefix("qu")
            return U_MEDIAL, word
    
        o_medial_cases = ["oa", "oă", "oe"]
        for o_medial_case in o_medial_cases:
            if word.startswith(o_medial_case):
                word = word.removeprefix("o")
                return O_MEDIAL, word
            
        if word.startswith("ua") or word.startswith("uô"):
            return None, word
        
        nucleuses = ['ê', 'y', 'ơ', 'a', 'â', 'ya']
        for nucleus in nucleuses:
            component = U_MEDIAL + nucleus
            if word.startswith(component):
                word = word.removeprefix("u")
                return U_MEDIAL, word
            
        return None, word

    @classmethod
    def get_nucleus(self, word: str) -> tuple[str, str]:
        nucleuses = list(VietnameseGraphemesToPhonemes.Nucleus.keys())
    
        for nucleus in nucleuses:
            if word.startswith(nucleus):
                word = word.removeprefix(nucleus)
                return nucleus, word

        return None, word

    @classmethod
    def get_coda(self, word: str) -> tuple[str, str]:
        codas = list(VietnameseGraphemesToPhonemes.Final.keys())
    
        if word in codas:
            return word
        
        return None
    
    @classmethod
    def split_grapheme(self, word: str) -> list[str, str, str]:
        onset, word = self.get_onset(word)
        
        medial, word = self.get_medial(word)

        nucleus, word = self.get_nucleus(word)

        coda = self.get_coda(word)
        
        return onset, medial, nucleus, coda

def analyze_Vietnamese_word(word: str) -> tuple[bool, tuple[str]]:
    tone, word = VietnameseDecomposer.get_tone(word)

    # in case the word has the structure of a Vietnamese word, we check whether it satisfies the rule of phoneme combination
    onset, medial, nucleus, coda = VietnameseDecomposer.split_grapheme(word)
    # handle the case where "y" is used as the nucleus
    if onset == "gi" and nucleus is None:
        nucleus = "i"
    if onset == "y" and tone is not None:
        onset = None
        nucleus = "y"

    if nucleus is None:
        return False, None
    # transform these graphemes into phonemes
    if onset:
        initial = VietnameseGraphemesToPhonemes.Initial[onset]
    else:
        initial = None
    if medial:
        glide = VietnameseGraphemesToPhonemes.Glide[medial]
    else:
        glide = None
    
    nucleus = VietnameseGraphemesToPhonemes.Nucleus[nucleus]
    
    if coda:
        final = VietnameseGraphemesToPhonemes.Final[coda]
    else:
        final = None

    return True, (initial, glide, nucleus, final, tone)

def is_Vietnamese(onset: str, medial: str, nucleus: str, coda: str, tone: str) -> bool:
    if nucleus is None:
        return False
    
    if onset == "k" and medial == "" and nucleus not in ["i", "y", "e", "ê", "iê", "yê", "ia", "ya"]:
        return False
    
    if onset == "c" and medial == "" and nucleus in ["i", "y", "e", "ê", "iê", "yê", "ia", "ya"]:
        return False
    
    if onset == "q" and not medial == "u":
        return False
    
    if onset == "gh" and medial == "" and nucleus not in ["i", "e", "ê", "iê"]:
        return False
    
    if onset == "g" and medial == "" and nucleus in ["i", "e", "ê", "iê"]:
        return False
    
    if onset == "ngh" and medial == "" and nucleus not in ["i", "e", "ê", "iê", "yê", "ia", "ya"]:
        return False
    
    if onset == "ng" and medial == "" and nucleus in ["i", "e", "ê", "iê", "yê", "ia", "ya"]:
        return False
    
    if onset in ["r", "gi"] and medial != "":
        return False
    
    if medial == "o" and nucleus not in ["a", "ă", "e"]:
        return False
    
    if medial == "u" and nucleus not in ['yê', 'ya', 'e', 'ê', 'y', 'ơ', "ô", 'a', 'â', 'ă']:
        return False
    
    if nucleus == "oo" and coda not in ["ng", "c"]:
        return False
    
    if nucleus == "ua" and coda != "":
        return False
    
    if nucleus == "ia" and coda != "":
        return False
    
    if nucleus == "ya" and coda != "":
        return False
    
    if nucleus in ["ua", "uô"] and coda == "ph":
        return False
    
    if nucleus in ["yê", "iê"] and coda == "":
        return False
    
    if nucleus in ["ă", "â"] and coda == "":
        return False
    
    if medial == "o" and nucleus in ["iê", "yê", "ia", "ya"]:
        return False
    
    if medial != "":
        if nucleus in ["u", "oo", "o", "ua", "uô", "ươ", "ưa", "ư"]:
            return False
        
        if nucleus in ["i", "e", "ê", "ia", "ya", "iê", "yê"] and coda in ["m", "ph"]:
            return False
        
    if coda == "o" and nucleus not in ["a", "e"]:
        return False
    
    if coda == "y" and nucleus not in ["a", "â"]:
        return False
    
    if coda == "i" and nucleus in ["ă", "â", "i", "e", "iê", "yê", "ia", "ya"]:
        return False
    
    if coda == "nh" and nucleus not in ["a", "i", "y", "ê"]:
        return False
    
    if coda == "ng" and nucleus not in ["a", "o", "ô", "u", "ư", "e", "iê", "ươ", "â", "ă", "uô", "oo"]:
        return False

    if coda == "ch" and nucleus not in ["i", "a", "ê", "y"]:
        return False

    if coda == "c" and nucleus in ["i", "ê", "e", "ơ"]:
        return False

    if nucleus == coda:
        return False

    return True

class VietnamesePhonemesToGraphemes:
    Initial: dict[str, list] = {
        None: [""],
        "f": ["ph"],
        "tʰ": ["th"],
        "ʝ": ["gi", "v", "d"],
        "ɣ": ["gh", "g", "r"],
        "t͡ɕ": ["ch"],
        "ʈ͡ʂ": ["tr"],
        "ɲ": ["nh"],
        "ŋ": ["ng"],
        "χ": ["kh"],
        "kʷ": ["qu"],
        "m": ["m"],
        "b": ["b"],
        "k": ["c"],
        "t": ["t"],
        "d": ["đ"],
        "n": ["n"],
        "r": ["gh", "g", "r"],
        "s": ["s", "x"],
        "l": ["l"],
        "h": ["h"],
    }
    
    Glide: dict[str, list] = {
        "u̯": ["u", "o"],
        None: [""],
    }

    Nucleus: dict[str, list] = {
        "iə": ["iê", "yê", "ia", "ya"],
        "uə": ["uô", "ua"],
        "ɯə": ["ươ", "ưa"],
        "u": ["u"],
        "a": ["a"],
        "ă": ["ă"],
        "ə̆": ["â"],
        "i": ["i", "y"],
        "ɛ": ["e"],
        "e": ["ê"],
        "ɯ": ["ư"],
        "ɔ": ["o", "oo"],
        "o": ["ô"],
        "ə": ["ơ"],
    }

    Final: dict[str, list] = {
        None: [""],
        "ŋ̟": ["nh"],
        "ŋ": ["ng"],
        "k̟": ["ch"],
        "j": ["i", "y"],
        "m": ["m"],
        "n": ["n"],
        "p": ["p"],
        "t": ["t", "c"],
        "k": ["c", "t"],
        "u̯": ["u", "o"],
    }

    Tone: dict[str, str] = {
        None: "",
        "˨˩": '\u0300',
        "˧˥": '\u0301',
        "˧ˀ˥": '\u0303',
        "˧˩": '\u0309',
        "˧ˀ˩": '\u0323',
    }