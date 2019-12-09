import argparse
import epub
import functools
import html2text
import os
import re
import sys

CHAPTERS = "chapters"

def epub_to_txt(
        epub_file_name,
        file_dir="epub-files",
        output_file_dir="txt-files",
        chapter_files_dir=None):
    if chapter_files_dir is None:
        chapter_files_dir = os.path.join(output_file_dir, CHAPTERS)
    _try_mkdirs(output_file_dir)
    _try_mkdirs(chapter_files_dir)

    html_to_text = html2text.HTML2Text()
    html_to_text.ignore_links = True

    # Ignore hidden files
    if epub_file_name[0] == '.':
        return
    # Ignore files that don't have the epub extension
    if os.path.splitext(epub_file_name)[1] != ".epub":
        return

    print("Opening file: %s" % epub_file_name)
    ebook = epub.open_epub(os.path.join(file_dir, epub_file_name))
    book_title = ebook.toc.title
    print("Starting on book: %s" % book_title)

    play_order = [nav_point.play_order for nav_point in ebook.toc.nav_map.nav_point]
    labels = [nav_point.labels[0][0] for nav_point in ebook.toc.nav_map.nav_point]
    source_references = [nav_point.src for nav_point in ebook.toc.nav_map.nav_point]

    chapter_label_source_tuples = list(zip(play_order, labels, source_references))

    full_book_content = list()
    for item in chapter_label_source_tuples:
        chapter_order = item[0]
        chapter_title = item[1]

        chapter_info_string = "Book: %s Chapter: %s titled: %s"\
            % (book_title, chapter_order, chapter_title)
        try:
            chapter_content = ebook.read_item(item[2])
        except Exception as e:
            print("Failed getting chapter: %s %s in book %s, exception: %s"
                % (chapter_order, chapter_title, ebook.toc.title, str(e)))
            ref_fixed = re.sub("#.*", "", item[2])
            try:
                chapter_content = ebook.read_item(ref_fixed)
                print("Success on retry! %s" % chapter_info_string)
            except:
                print("FAILED ON RETRY TOO for book titled: %s with ref: %s."
                    % (book_title, ref_fixed))
        chapter_content = html_to_text.handle(str(chapter_content.decode('utf-8')))
        full_book_content.append((chapter_order, chapter_title, chapter_content))
    with open(os.path.join(output_file_dir, epub_file_name.replace(".epub", ".txt")), "w") as txt_file:
        for chapter_tuple in full_book_content:
            order = chapter_tuple[0]
            title = chapter_tuple[1]
            content = chapter_tuple[2]
            txt_file.write(content)

            chapter_file_name = epub_file_name.replace(".epub", "")
            chapter_file_name += "--" + order.zfill(5) + "--" + title
            chapter_file_name += ".txt"
            with open(os.path.join(chapter_files_dir, chapter_file_name), "w") as chapter_txt_file:
                chapter_txt_file.write(content)

    ebook.close()

def _try_mkdirs(dir_name):
    try:
        os.makedirs(dir_name)
    except Exception as e:
        print("Failed to mkdirs: %s" % str(e))
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--epub-file-path', default=None)
    parser.add_argument('-o', '--output-dir', default=".")
    parser.add_argument('-c', '--output-chapter-dir', default=None)
    args = parser.parse_args()

    if args.epub_file_path is None:
        print("Must provide an epub file!")
        sys.exit(1)

    epub_to_txt(
        os.path.basename(args.epub_file_path),
        file_dir=os.path.dirname(args.epub_file_path),
        output_file_dir=args.output_dir,
        chapter_files_dir=args.output_chapter_dir)
    print("Done!")
