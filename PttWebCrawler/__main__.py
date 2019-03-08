import sys
import argparse
from PttWebCrawler.crawler import PttWebCrawler


__version__ = '1.0-0.1'

def main():
    """The main routine."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, 
        description=(
        "A crawler for the web version of PTT, the largest online community in Taiwan."
        "Input: board name and page indices (or articla ID)"
        "Output: BOARD_NAME-START_INDEX-END_INDEX.json (or BOARD_NAME-ID.json)"
        ))
    parser.add_argument('-b', metavar='BOARD_NAME', help='Board name', required=True)
    parser.add_argument('-o', '--output-dir', help='output directory', 
                        default='data')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', metavar=('START_INDEX', 'END_INDEX'), type=int, nargs=2, help="Start and end index")    
    group.add_argument('-a', metavar='URL', help='article id')
    group.add_argument('-n', metavar='N', help='number of pages to retrieve')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)

    args = parser.parse_args()
    
    ptt = PttWebCrawler(args.output_dir)
    if args.b:
        board = args.b
        
    if args.i:
        start = args.i[0]
        if args.i[1] == -1:
            end = ptt.getLastPage(board)
        else:
            end = args.i[1]
        
        ptt.parse_articles(start, end, board)
    
    if args.n:
        end = ptt.getLastPage(board)
        start = end - int(args.n) + 1
        ptt.parse_articles(start, end, board)

    if args.a:
        article_id = args.a
        ptt.parse_article(article_id, board)

if __name__ == "__main__":
    main()