import axios from 'axios';
import * as cheerio from 'cheerio';

export default async function handler(req, res) {
  const { url } = req.query;

  if (!url || !url.includes('mp.weixin.qq.com/mp/appmsgalbum')) {
    return res.status(400).json({ error: 'URL album không hợp lệ.' });
  }

  try {
    const { data } = await axios.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });

    const $ = cheerio.load(data);
    const items = [];

    $('.album__item').each((i, el) => {
      const title = $(el).find('.album__item-title').text().trim();
      const href = $(el).find('a.album__item-link').attr('href');

      if (title && href) {
        items.push({
          title,
          url: href.startsWith('http') ? href : `https://mp.weixin.qq.com${href}`
        });
      }
    });

    res.setHeader('Cache-Control', 's-maxage=600');
    res.status(200).json(items);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Không thể lấy dữ liệu album WeChat.' });
  }
}
