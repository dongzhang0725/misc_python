#!/usr/bin/env python

"""

Name: freebayes_vcf2fa.py

Author: Michael G. Harvey
Date: 4 August 2014

Description: This script takes a vcf file output from freebayes (Garrison and Marth 2012), 
a program for calling genotypes and outputting information from bam files, and converts it
to genotype sequences for use in e.g. coalescent modeling and phylogenetics. The input vcf
must have been run with the freebayes option --report-monomorphic, which outputs all bases
including invariant sites. This script uses the freebayes genotype calls, but filters out 
alleles if they fall below a user-defined minimum coverage value. It is designed for 
either haploid or diploid individuals (ploidy must be assigned in the options). Any loci 
containing more alleles than the set ploidy level will be removed from the output (and are
listed in a separate summary file). 

Usage:

python freebayes_vcf2fa.py in_file out_file summary_file ploidy min_cov

"""

import os
import sys
import re
import argparse


def get_args():
	parser = argparse.ArgumentParser(
			description="""Program description""")
	parser.add_argument(
			"in_file",
			type=str,
			help="""The input vcf file from freebayes"""
		)
	parser.add_argument(
			"out_file",
			type=str,
			help="""The output fasta file"""
		)
	parser.add_argument(
			"summary_file",
			type=str,
			help="""The output file summarizing paralogous reads"""
		)
	parser.add_argument(
			"ploidy",
			type=int,
			help="""The ploidy of the sampled individual"""
		)
	parser.add_argument(
			"min_cov",
			type=int,
			help="""The minimum number of observations to output an allele to fasta file"""
		)
	return parser.parse_args()


def unphase(a1, a2):	
	a1 = str(a1.upper())
	a2 = str(a2.upper())
	if a1 == "A":
		if a2 == "C":
			code = "M"
		elif a2 == "G":
			code = "R"
		elif a2 == "T":
			code = "W"					
		elif a2 == "A":
			code = "A"					
	elif a1 == "C":
		if a2 == "A":
			code = "M"
		elif a2 == "G":
			code = "S"
		elif a2 == "T":
			code = "Y"
		elif a2 == "C":
			code = "C"					
	elif a1 == "G":
		if a2 == "A":
			code = "R"
		elif a2 == "C":
			code = "S"				
		elif a2 == "T":
			code = "K"
		elif a2 == "G":
			code = "G"					
	elif a1 == "T":
		if a2 == "A":
			code = "W"
		elif a2 == "C":
			code = "Y"					
		elif a2 == "G":
			code = "K"	
		elif a2 == "T":
			code = "T"	
	else:
		print "ERROR"				
	return str(code)


def main():
	args = get_args()
	if args.ploidy not in [1, 2]:
		print "Error: Ploidy must be set to either 1 or 2"
		exit()
	infile = open("{0}".format(args.in_file), 'r')
	out = open("{0}".format(args.out_file), 'wb')
	summary = open("{0}".format(args.summary_file), 'wb')
	summary.write("Loci with more alleles than the set ploidy level:\n")
	seq = list()
	firstline = True
	j = 0
	k = 0
	for line in infile:
		if not line.startswith("#"):
			parts = line.split()
			nameparts = parts[0].split("|") # Remove for dist
			name = nameparts[0] # Edit for dist
			if not firstline == True:
				if name != prev_name:
					out.write(">{0}\n".format(name))
					out.write("{0}\n".format(''.join(seq)))
					seq = list()			
			info = parts[7]
			match = re.search('DP=(\d{1,10})', info)
			depth = int(match.group(1))
			base = None 
			if depth < args.min_cov: # Output n's for sites with low read depth
				base = "n"*len(list(ref_allele))			
			else:
				ref_allele = parts[3]
				alt_allele = parts[4]
				if alt_allele.rstrip() == ".": # If site corresponds to reference
					base = ref_allele
				else:
					alleles = list()
					depths = list()
					gt_info = parts[-1]					
					info_parts = gt_info.split(":")
					ref_depth = int(info_parts[2])
							
					# Get alleles and depths
					alleles.append(ref_allele)
					depths.append(ref_depth)
					alt_depth = info_parts[4]
					if "," not in alt_allele: # If only a single alt allele
						alleles.append(alt_allele)
						depths.append(int(alt_depth))
					elif "," in alt_allele: # If multiple alt alleles
						list_alt_alleles = alt_allele.split(",")
						alt_depths = alt_depth.split(",")
					 	for i, list_alt_allele in enumerate(list_alt_alleles):
				 			alleles.append(list_alt_allele)
				 			depths.append(int(alt_depths[i]))
					
					# Get genotypes and filter them by coverage
					gt = info_parts[0]
					gt_parts = gt.split("/")
					gt_filtereds = list()
					for gt_part in gt_parts:
						if depths[int(gt_part)] >= args.min_cov:
							gt_filtereds.append(gt_part)
					gt_alleles = list()
					gt_depths = list()
					for gt_filtered in gt_filtereds:
						gt_alleles.append(alleles[int(gt_filtered)])
						gt_depths.append(depths[int(gt_filtered)])
					gt_allele_set = list()
					gt_allele_set = list(set(gt_alleles))

					# Call bases
					if len(gt_allele_set) > 2:
						summary.write("{0}\n".format(name))
						print "Locus {0} contains paralogous reads".format(name)
						j += 1
					elif len(gt_allele_set) == 2:
						if args.ploidy == 1:
							summary.write("{0}\n".format(name))
							print "Locus {0} contains paralogous reads".format(name)
							j += 1							
						elif args.ploidy == 2:
							if len(gt_allele_set[0]) == len(gt_allele_set[1]) == 1:
								base = unphase(gt_allele_set[0], gt_allele_set[1])
							else:
								# Change this to be based on coverage?
								gt_allele_set[0]
							k += 1
							print gt_filtereds
							print gt_alleles
							print gt_depths
							print base
					elif len(gt_allele_set) == 1:
						base = gt_alleles[0]
					elif len(gt_allele_set) == 0:
						base = "n"*len(list(ref_allele))
					#print base
			if base is not None:
				seq.append(base)
			prev_name = name
			firstline = False
	print "{0} loci with paralogous reads detected and removed from output".format(j)
	print "{0} heterozygous sites (diploid samples only)".format(k)
	infile.close()
	out.close()
									
if __name__ == '__main__':
    main()