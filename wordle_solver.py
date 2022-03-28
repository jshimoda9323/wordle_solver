#!/usr/bin/env python3

import sys
import re
import random
import string
import pickle
import os.path

freq_file = "en_words_1_1-64.txt"
debug_words_eliminated = [  ]
save_file = "dictionary.save"

if len(sys.argv) != 2:
    print("wordle_solver.py <integer_word_length>", file=sys.stderr)
    sys.exit(1)

word_length = int(sys.argv[1])
word_set = set()
freq_dict = {}
letter_freq = {}
save_file = save_file + "." + str(word_length)
word_regex = re.compile("^[A-Z]+$")
color_regex = re.compile("[bgyu]+")

# Read in all words with specified length
#print("Reading frequency dictionary...")
if os.path.exists(save_file):
    with open(save_file, "rb") as fd:
        save_info = pickle.load(fd)
        freq_dict = save_info[0]
        letter_freq = save_info[1]
    word_set = set(freq_dict.keys())
else:
    freq_line_count = 0
    for letter in string.ascii_uppercase[:26]:
        letter_freq[letter] = 0
    with open(freq_file, "r") as fd: lines = fd.readlines()
    for line in lines:
        parts = line.strip().split(' ')
    
        if len(parts) < 3: continue
    
        word = parts[0].upper()
        if len(word) == word_length and bool(word_regex.match(word)):
            # (rank, freq)
            freq_dict[word] = (freq_line_count, int(parts[2]))
            word_set.add(word)
            if len(word_set) < 10000:
                for l in word:
                    letter_freq[l] += 1
        freq_line_count += 1
    del(lines)
    with open(save_file, "wb") as fd:
        pickle.dump([freq_dict, letter_freq], fd)

print("Number of "+str(word_length)+" letter words: "+str(len(word_set)))

# Get the most common letters in the dictionary of n-letter words
letters_to_find = list(letter for letter, fq in sorted(letter_freq.items(), key=lambda x: x[1], reverse=True))[:word_length]
# Print the top 5 most frequent words containing all the most frequent letters
def word_contains_letters(word, letter_list):
    for letter in letter_list:
        if letter not in word:
            return(False)
    return(True)
suggested_initial_word_list = list((word, freq_dict[word]) for word in word_set if word_contains_letters(word, letters_to_find))
suggested_initial_word_list.sort(key=lambda x:x[1][1], reverse=True)
print("Top 5 suggested initial guesses:")
for elem in suggested_initial_word_list[:5]:
    print("{:s} {:d}".format(elem[0], elem[1][1]))

known_letters = list("_" for l in range(word_length))

eligibility = {}
while len(word_set) > 1:
    black = []
    green = []
    yellow = []
    print("Known letters: "+str("".join(known_letters)))

    while(True):
        print("Enter a "+str(word_length)+" letter word: ", end="", flush=True)
        guess = sys.stdin.readline().strip().upper()
        if len(guess) == word_length and bool(word_regex.match(guess)):
            break
        print("Error.", file=sys.stderr)
    while(True):
        print("Enter colors: ", end="", flush=True)
        colors = sys.stdin.readline().strip().lower()
        if len(colors) == word_length and bool(color_regex.match(colors)):
            break
        print("Error.", file=sys.stderr)

    for i in range(word_length):
        if colors[i] == 'g':
            green.append((guess[i], i))
        elif colors[i] == 'y':
            yellow.append((guess[i], i))
        elif colors[i] == 'b':
            black.append((guess[i], i))
        elif colors[i] == 'u':
            pass
        else:
            print("Internal Error: invalid color.")
            sys.exit(2)

    # Green letters are absolutely known - reduce the word set based on known letters
    for (letter, pos) in green:
        known_letters[pos] = letter
        if letter not in eligibility:
            eligibility[letter] = [1, word_length, [True for i in range(word_length)]]
        eligibility[letter][0] -= 1
        eligibility[letter][2][pos] = False
        word_set = set(word for word in word_set if word[pos] == letter)

    #print("DEBUG eligibility")
    #print(eligibility)

    # Process yellow and black letters together
    yellow_black = {}
    for (yellow_letter, yellow_pos) in yellow:
        if yellow_letter not in yellow_black:
            # [ min, max, disallowed_array ]
            yellow_black[yellow_letter] = [0, word_length, [False for i in range(word_length)]]
        yellow_black[yellow_letter][0] += 1 # Min += 1
        yellow_black[yellow_letter][2][yellow_pos] = True
    for (black_letter, black_pos) in black:
        if black_letter not in yellow_black:
            # [ min, max, disallowed_array ]
            yellow_black[black_letter] = [0, word_length, [False for i in range(word_length)]]
        yellow_black[black_letter][1] = yellow_black[black_letter][0] # max = min
        yellow_black[black_letter][2][black_pos] = True

    #print("DEBUG yellow_black")
    #print(yellow_black)

    for (letter, restriction) in yellow_black.items():
        if letter not in eligibility:
            eligibility[letter] = [0, word_length, [True for i in range(word_length)]]
        e = eligibility[letter]
        if e[0] < restriction[0]:
            e[0] = restriction[0]
        if e[1] > restriction[1]:
            e[1] = restriction[1]
        disallowed_list = restriction[2]
        for pos in range(len(disallowed_list)):
            if disallowed_list[pos]:
                e[2][pos] = False

    #print("DEBUG eligibility")
    #print(eligibility)

    # Filter out words by appling eligibility
    new_word_set = set()
    for word in word_set:
        eligible = True
        letter_counts = {}
        # Exclude all words containing letters in invalid positions
        for letter_pos in range(len(word)):
            letter = word[letter_pos]
            if known_letters[letter_pos] == letter:
                continue
            if letter not in letter_counts:
                letter_counts[letter]  = 0
            letter_counts[letter] += 1
            if letter in eligibility:
                if not eligibility[letter][2][letter_pos]:
                    if word in debug_words_eliminated:
                        print("1.1 word eliminated: "+str(word))
                    eligible = False
                    break
        if not eligible:
            continue
        # Exclude all words containing invalid letter frequency
        for (letter, letter_count) in letter_counts.items():
            if letter in eligibility:
                if eligibility[letter][0] > letter_count:
                    if word in debug_words_eliminated:
                        print("2.1 word eliminated: "+str(word))
                    eligible = False
                    break
                elif eligibility[letter][1] < letter_count:
                    if word in debug_words_eliminated:
                        print("2.2 word eliminated: "+str(word)+" letter="+str(letter)+" eligibility[letter][1]="+str(eligibility[letter][1]))
                    eligible = False
                    break
                else:
                    pass
        if not eligible:
            continue
        # Exclude all words not containing required letters
        for letter_eli in eligibility.keys():
            if eligibility[letter_eli][0] > 0:
                if letter_eli not in letter_counts:
                    if word in debug_words_eliminated:
                        print("3.1 word eliminated: "+str(word))
                    eligible = False
                    break
                else:
                    if letter_counts[letter_eli] < eligibility[letter_eli][0]:
                        if word in debug_words_eliminated:
                            print("3.2 word eliminated: "+str(word))
                        eligible = False
                        break
            if letter_eli in letter_counts and letter_counts[letter_eli] > eligibility[letter_eli][1]:
                if word in debug_words_eliminated:
                    print("3.3 word eliminated: "+str(word))
                eligible = False
                break
        if not eligible:
            continue
        new_word_set.add(word)
    word_set = new_word_set
        
    # Sort the words by frequency then display top 16
    words_by_freq = list(((word, freq_dict[word][1], freq_dict[word][0]) for word in word_set))
    words_by_freq.sort(key=lambda x: x[1], reverse=True)

    print("Possible words: "+str(len(words_by_freq)))
    print("TOP 16: {word:10s} {freq:13s} {rank:11s}".format(word="Word", freq="Freq", rank="Global Rank"))
    print("        {word:10s} {freq:13s} {rank:11s}".format(word="----------", freq="-------------", rank="-----------"))
    for i in range(min(16,len(words_by_freq))):
        if i < len(words_by_freq):
            print("{idx:>7d} {word:10s} {freq:<13d} {rank:<11d}".format(idx=i+1, word=str(words_by_freq[i][0]), freq=words_by_freq[i][1], rank=words_by_freq[i][2]))
    print("        {word:10s} {freq:13s} {rank:11s}".format(word="----------", freq="-------------", rank="-----------"))

